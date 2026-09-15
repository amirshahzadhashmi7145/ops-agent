"""Device-aware SOP routing based on serial, model, and issue keywords."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sop import SopDocument, SopProcess, SopProcessingStatus
from app.services.sim_diagnostics import build_lookup_response, find_devices_by_query
from app.services.sop_retrieval import _process_result, search_sop_processes

SERIAL_PATTERN = re.compile(r"\b([A-Z]{2,3}-[A-Z0-9]+-\d+)\b", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")

CONNECT_MODEL_MARKERS = ("beam2", "beam 2", "nexar one", "b2-mini", "b2 mini")
CLASSIC_MODEL_MARKERS = ("nexar pro", "nexc1", "nexc2", "nexs1", "classic")
CONNECTIVITY_MARKERS = (
    "won't connect",
    "wont connect",
    "can't connect",
    "cant connect",
    "disconnect",
    "pairing",
    "pair ",
    "wifi",
    "wi-fi",
    "bluetooth",
    "lte",
    "sim ",
    "onboarding",
    "turquoise",
    "blinking light",
)
HARDWARE_MARKERS = (
    "power",
    "battery",
    "red light",
    "blinking red",
    "hardware",
    "defective",
    "broken",
    "irq",
    "sd card",
    "not recording",
    "reboot",
    "restart",
    "swollen",
    "bloated",
)

DOC_CLASSIC = "SOP - Nexar Classic App Connectivity & Pairing"
DOC_CONNECT = "SOP - Connectivity for Nexar Connect V2"
DOC_HARDWARE = "SOP - Hardware Malfunction"


def _extract_serial(message: str) -> str | None:
    match = SERIAL_PATTERN.search(message)
    return match.group(1).upper() if match else None


def _extract_email(message: str) -> str | None:
    match = EMAIL_PATTERN.search(message)
    return match.group(0) if match else None


def _message_lower(message: str) -> str:
    return message.lower()


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _primary_device(
    matches: list[tuple[Any, Any, dict]],
    *,
    serial: str | None,
) -> tuple[Any, Any, dict] | None:
    if not matches:
        return None
    if serial:
        for device, customer, profile in matches:
            if device.serial_number.upper() == serial.upper():
                return device, customer, profile
    return matches[0]


def resolve_device_routing(db: Session, message: str) -> dict[str, Any]:
    """Return routing hints from device lookup and issue keywords."""
    msg = _message_lower(message)
    serial = _extract_serial(message)
    email = _extract_email(message)

    query = serial or email or ""
    matches = find_devices_by_query(db, query) if query else []
    primary = _primary_device(matches, serial=serial)

    routing: dict[str, Any] = {
        "serial": serial,
        "email": email,
        "device_found": primary is not None,
    }

    if primary:
        device, customer, profile = primary
        lookup = build_lookup_response(device, customer, profile)
        routing["device"] = lookup
        routing["camera_family"] = profile.get("camera_family")
        routing["model"] = profile.get("model") or device.model
        routing["segment"] = profile.get("segment", "consumer")

    family = routing.get("camera_family")
    model = str(routing.get("model") or "").lower()

    if _has_any(msg, CONNECT_MODEL_MARKERS) or any(
        token in model for token in ("beam2", "nexar one")
    ):
        family = "connect"
    if _has_any(msg, CLASSIC_MODEL_MARKERS) or "nexar pro" in model:
        family = "classic"

    # Email-only lookups can return mixed Classic + Connect cameras. Do not pick
    # a family (and lock a diagnostic SOP) from whichever device came back first.
    if email and not serial and len(matches) > 1:
        families = {
            (profile.get("camera_family") or "").lower()
            for _device, _customer, profile in matches
        }
        families.discard("")
        if len(families) > 1:
            family = None
            routing["camera_family"] = None

    is_hardware = _has_any(msg, HARDWARE_MARKERS)
    is_connectivity = _has_any(msg, CONNECTIVITY_MARKERS)
    # An account lookup ("list devices for this email") is not a pairing/LTE ticket.
    should_lock_diagnostic_sop = bool(is_hardware or is_connectivity)

    preferred_doc: str | None = None
    preferred_process: str | None = None
    mandatory_tools: list[str] = []
    instructions: list[str] = []

    if should_lock_diagnostic_sop and family == "classic":
        if is_hardware:
            preferred_doc = DOC_HARDWARE
            preferred_process = "Hardware Malfunction"
            mandatory_tools = ["getDeviceLookup", "getDeviceHealth"]
            instructions.append(
                "Classic camera hardware issue. Do NOT use getClassicDiagnostic or the Connect connectivity SOP."
            )
        else:
            preferred_doc = DOC_CLASSIC
            preferred_process = "Nexar Classic App Connectivity"
            mandatory_tools = ["getClassicDiagnostic"]
            instructions.append(
                "Classic camera app connectivity issue. Do NOT use getSimTriage or Connect-only tools."
            )
    elif should_lock_diagnostic_sop and family == "connect":
        if is_hardware:
            preferred_doc = DOC_HARDWARE
            preferred_process = "Hardware Malfunction"
            mandatory_tools = ["getDeviceLookup", "getDeviceHealth"]
            instructions.append(
                "Connect camera hardware issue. Call getDeviceHealth before escalating. "
                "If has_power_issues is false, perform power troubleshooting steps — do not escalate immediately."
            )
        else:
            preferred_doc = DOC_CONNECT
            preferred_process = "Sim Triage"
            mandatory_tools = ["getDeviceLookup", "getSimTriage"]
            instructions.append(
                "Connect camera connectivity issue. Do NOT use getClassicDiagnostic. "
                "Start with getDeviceLookup, then getSimTriage."
            )
            instructions.append(
                "After getSimTriage: if recommended_action is reactivate_sim call reactivateSim; "
                "if recommended_action is uplift_25gb call createLTEQuota25GB; "
                "if recommended_action is escalate call ticketEscalate with ticketInternalNote."
            )

    if routing.get("segment") == "fleets":
        instructions.append("Fleet customer — escalate to fleet queue per SOP.")

    if not should_lock_diagnostic_sop and (routing.get("email") or routing.get("serial")):
        instructions.append(
            "This is an account or device lookup, not a diagnostic ticket. "
            "Use lookup_customer_by_email / list_customer_devices / getDeviceLookup. "
            "Do not follow a connectivity or hardware SOP unless the customer describes a pairing, LTE, or hardware issue."
        )

    routing["preferred_document_title"] = preferred_doc
    routing["preferred_process_hint"] = preferred_process
    routing["mandatory_first_tools"] = mandatory_tools
    routing["routing_instructions"] = instructions
    routing["is_hardware"] = is_hardware
    routing["is_connectivity"] = is_connectivity
    return routing


def _find_process_in_document(
    db: Session,
    document_title: str,
    process_hint: str | None,
) -> dict[str, Any] | None:
    rows = (
        db.query(SopProcess, SopDocument)
        .join(SopDocument, SopProcess.document_id == SopDocument.id)
        .filter(
            SopDocument.title == document_title,
            SopDocument.active.is_(True),
            SopDocument.enabled.is_(True),
            SopDocument.processing_status == SopProcessingStatus.ready,
        )
        .all()
    )
    if not rows:
        return None

    if process_hint:
        hint = process_hint.lower()
        for process, document in rows:
            if hint in (process.title or "").lower() or hint in (process.process_key or "").lower():
                content = f"{process.title}\n{process.description}"
                return _process_result(process, document, 0.95, content)

    process, document = rows[0]
    content = f"{process.title}\n{process.description}"
    return _process_result(process, document, 0.9, content)


def is_confident_match(
    best: dict[str, Any] | None,
    matches: list[dict[str, Any]],
    *,
    threshold: float,
    margin: float,
) -> bool:
    """A match is confident only if it clears the threshold AND beats the runner-up
    by ``margin``. The margin is what stops a near-tie (two similar SOPs scoring
    almost the same) from being locked to the wrong one."""
    if not best:
        return False
    score = float(best.get("score", 0))
    if score < threshold:
        return False
    runner_up = next(
        (m for m in matches if m.get("process_id") != best.get("process_id")),
        None,
    )
    if runner_up is not None and (score - float(runner_up.get("score", 0))) < margin:
        return False
    return True


def choose_sop_process(
    db: Session,
    user_message: str,
    *,
    routing: dict[str, Any] | None = None,
    top_k: int | None = None,
    threshold: float | None = None,
    margin: float | None = None,
) -> dict[str, Any]:
    """Choose an SOP process and say whether we're confident enough to auto-lock it.

    Returns ``{"best", "matches", "confident", "routing"}``. Device routing (a serial
    the user mentioned) is treated as high-confidence; otherwise the semantic top-1
    must clear the threshold AND beat the runner-up by a margin. When not confident,
    the caller should defer to the model (show it the shortlist) rather than guess.
    """
    threshold = settings.sop_auto_match_threshold if threshold is None else threshold
    margin = settings.sop_auto_match_margin if margin is None else margin
    routing = routing or resolve_device_routing(db, user_message)
    preferred_doc = routing.get("preferred_document_title")
    preferred_hint = routing.get("preferred_process_hint")

    if preferred_doc:
        routed = _find_process_in_document(db, preferred_doc, preferred_hint)
        if routed:
            routed["routing"] = routing
            routed["score"] = max(
                float(routed.get("score", 0)), 0.95 if routing.get("device_found") else 0.88
            )
            return {"best": routed, "matches": [routed], "confident": True, "routing": routing}

    matches = search_sop_processes(db, user_message, top_k=top_k)
    if not matches:
        return {"best": None, "matches": [], "confident": False, "routing": routing}

    # A device-preferred document, when present, wins its semantic match outright.
    if preferred_doc:
        for match in matches:
            if match.get("document_title") == preferred_doc:
                match = {**match, "score": float(match.get("score", 0)) + 0.2, "routing": routing}
                return {"best": match, "matches": matches, "confident": True, "routing": routing}

    # Plain account lookups ("list devices for this email") must not auto-lock a
    # pairing/LTE/hardware SOP just because embeddings are close.
    if not routing.get("is_connectivity") and not routing.get("is_hardware"):
        diagnostic_titles = { "Nexar Classic App Connectivity", "Sim Triage", "Hardware Malfunction"}
        filtered = [m for m in matches if m.get("title") not in diagnostic_titles]
        if filtered:
            matches = filtered

    best = {**matches[0], "routing": routing}
    confident = is_confident_match(best, matches, threshold=threshold, margin=margin)
    return {"best": best, "matches": matches, "confident": confident, "routing": routing}


def routing_prompt_block(routing: dict[str, Any]) -> str:
    lines = ["### Device routing context"]
    device = routing.get("device")
    if device:
        lines.append(
            f"Identified device: {device.get('model')} ({device.get('serial_number')}), "
            f"family={routing.get('camera_family')}, segment={routing.get('segment')}."
        )
    elif routing.get("serial"):
        lines.append(f"Mentioned serial: {routing['serial']} (not found in demo data).")
    if routing.get("preferred_document_title"):
        lines.append(f"Preferred SOP document: {routing['preferred_document_title']}.")
    if routing.get("preferred_process_hint"):
        lines.append(f"Preferred process: {routing['preferred_process_hint']}.")
    for instruction in routing.get("routing_instructions") or []:
        lines.append(f"- {instruction}")
    tools = routing.get("mandatory_first_tools") or []
    if tools:
        lines.append(f"Call these tools first (in order): {', '.join(f'`{t}`' for t in tools)}.")
    return "\n".join(lines)
