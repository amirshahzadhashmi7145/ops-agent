#!/usr/bin/env python3
"""Live grounding evaluation against a running Ops Agent API.

Usage (host, with stack up):
  python3 scripts/grounding_eval.py
  API_BASE=http://127.0.0.1:8001 python3 scripts/grounding_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001").rstrip("/")
USER = os.environ.get("OPS_USER", "grounding-eval@example.com")
TOKEN = os.environ.get("OPS_API_TOKEN", "")


def _headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Ops-User": USER,
        "Accept": "application/x-ndjson, application/json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def api_get(path: str):
    req = urllib.request.Request(f"{API_BASE}{path}", headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def stream_chat(message: str, conversation_id: str | None = None) -> dict:
    payload: dict = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/chat/stream",
        data=body,
        headers=_headers(),
        method="POST",
    )
    events: list[dict] = []
    final = ""
    conv_id = conversation_id
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line:
                continue
            event = json.loads(line)
            events.append(event)
            if event.get("type") == "final_answer":
                final = event.get("content") or ""
            if event.get("type") == "done":
                conv_id = event.get("conversation_id") or conv_id
    return {"events": events, "final": final, "conversation_id": conv_id}


@dataclass
class CaseResult:
    name: str
    ok: bool
    detail: str
    final: str = ""
    event_types: list[str] = field(default_factory=list)


def event_types(events: list[dict]) -> list[str]:
    return [e.get("type", "?") for e in events]


def has_type(events: list[dict], *types: str) -> bool:
    wanted = set(types)
    return any(e.get("type") in wanted for e in events)


def run_inventory() -> CaseResult:
    try:
        refs = api_get("/api/kb/references")
        sops = api_get("/api/sops/documents")
        tools = api_get("/api/resources")
    except Exception as exc:  # noqa: BLE001
        return CaseResult("inventory", False, f"API unreachable: {exc}")

    ready_refs = [r for r in refs if r.get("processing_status") == "ready" and r.get("enabled", True)]
    ready_sops = [s for s in sops if s.get("processing_status") == "ready" and s.get("enabled", True)]
    active_tools = [t for t in tools if t.get("active")]
    ok = len(ready_refs) >= 5 and len(ready_sops) >= 3 and len(active_tools) >= 5
    detail = (
        f"articles_ready={len(ready_refs)}/{len(refs)} "
        f"workflows_ready={len(ready_sops)}/{len(sops)} "
        f"tools_active={len(active_tools)}/{len(tools)}"
    )
    if not ok:
        detail += " — seed looks empty; restart backend or re-run playbook seed"
    return CaseResult("inventory", ok, detail)


def run_cases() -> list[CaseResult]:
    results: list[CaseResult] = []

    # 1) Policy question must hit Articles (KB search), not invent warranty terms.
    try:
        out = stream_chat(
            "What is Meridian's warranty policy for Shopify purchases and Amazon purchases?"
        )
        types = event_types(out["events"])
        text = out["final"].lower()
        grounded = has_type(out["events"], "kb_search")
        mentions_amazon = "amazon" in text
        invents_years = "lifetime warranty" in text or "5 year" in text or "five-year" in text
        ok = grounded and mentions_amazon and not invents_years
        results.append(
            CaseResult(
                "warranty_policy_kb",
                ok,
                f"kb_search={grounded} amazon_mentioned={mentions_amazon} invents_lifetime={invents_years}",
                final=out["final"][:500],
                event_types=types,
            )
        )
        conv = out["conversation_id"]
    except Exception as exc:  # noqa: BLE001
        results.append(CaseResult("warranty_policy_kb", False, str(exc)))
        conv = None

    # 2) Follow-up should re-search, not answer from memory only.
    if conv:
        try:
            out = stream_chat("Tell me more about the out of warranty options.", conversation_id=conv)
            types = event_types(out["events"])
            grounded = has_type(out["events"], "kb_search")
            text = out["final"].lower()
            couponish = any(w in text for w in ("coupon", "discount", "out of warranty", "accessory"))
            ok = grounded and couponish
            results.append(
                CaseResult(
                    "followup_researches_kb",
                    ok,
                    f"kb_search={grounded} coupon_or_discount={couponish}",
                    final=out["final"][:500],
                    event_types=types,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(CaseResult("followup_researches_kb", False, str(exc)))

    # 3) Operational workflow should match SOP / call tools, not invent cancel success.
    try:
        out = stream_chat(
            "Please cancel the subscription for customer alex.rivera@example.com"
        )
        types = event_types(out["events"])
        used_sop_or_tools = has_type(
            out["events"],
            "sop_matched",
            "sop_search",
            "sop_step",
            "tool_call",
            "forced_tool_call",
            "resource_called",
        )
        text = out["final"].lower()
        fake_success = "successfully cancelled" in text and not used_sop_or_tools
        ok = used_sop_or_tools and not fake_success
        results.append(
            CaseResult(
                "cancel_subscription_tools",
                ok,
                f"sop_or_tools={used_sop_or_tools} fake_success={fake_success}",
                final=out["final"][:500],
                event_types=types,
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(CaseResult("cancel_subscription_tools", False, str(exc)))

    # 4) Device lookup must use tools for a known serial — no invented health.
    try:
        out = stream_chat("What is the health status of lock serial MD-GUARD-20022?")
        types = event_types(out["events"])
        used_tools = has_type(
            out["events"],
            "tool_call",
            "forced_tool_call",
            "resource_called",
            "sop_matched",
            "sop_search",
            "sop_step",
        )
        text = out["final"].lower()
        # Should not invent a random serial or claim perfect health without tools.
        invents = ("md-guard-99999" in text) or (
            not used_tools and "online" in text and "healthy" in text
        )
        ok = used_tools and not invents
        results.append(
            CaseResult(
                "device_health_tools",
                ok,
                f"tools_or_workflow={used_tools} invents={invents}",
                final=out["final"][:500],
                event_types=types,
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(CaseResult("device_health_tools", False, str(exc)))

    # 5) Trap: ask about a fake policy that is NOT in the KB — should refuse / not invent.
    try:
        out = stream_chat(
            "According to Meridian policy, do we offer a free lifetime battery replacement program called BatteryForever?"
        )
        types = event_types(out["events"])
        text = out["final"].lower()
        affirms_fake = (
            "yes" in text[:80]
            and "batteryforever" in text
            and "do not" not in text
            and "don't" not in text
            and "no " not in text
            and "not " not in text
        )
        # Acceptable: says it doesn't know / can't find / no such program.
        hedges = any(
            p in text
            for p in (
                "don't see",
                "do not see",
                "couldn't find",
                "could not find",
                "no such",
                "not find",
                "not listed",
                "no information",
                "don't have",
                "do not have",
                "unable to find",
                "not aware",
                "no policy",
            )
        )
        ok = (not affirms_fake) and (hedges or has_type(out["events"], "kb_search"))
        results.append(
            CaseResult(
                "refuse_fake_policy",
                ok,
                f"affirms_fake={affirms_fake} hedges={hedges} kb_search={has_type(out['events'], 'kb_search')}",
                final=out["final"][:500],
                event_types=types,
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(CaseResult("refuse_fake_policy", False, str(exc)))

    return results


def main() -> int:
    print(f"API_BASE={API_BASE}")
    inv = run_inventory()
    print(f"[{'PASS' if inv.ok else 'FAIL'}] {inv.name}: {inv.detail}")
    if not inv.ok and "unreachable" in inv.detail.lower():
        print("Start the stack first: docker compose up --build")
        return 2

    results = [inv, *run_cases()]
    failed = [r for r in results if not r.ok]
    print("\n=== Case details ===")
    for r in results:
        print(f"\n[{'PASS' if r.ok else 'FAIL'}] {r.name}")
        print(f"  {r.detail}")
        if r.event_types:
            print(f"  events: {r.event_types}")
        if r.final:
            preview = r.final.replace("\n", " ")[:240]
            print(f"  answer: {preview}")

    print(f"\nSummary: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"Cannot reach API at {API_BASE}: {exc}")
        print("Start the stack: docker compose up --build")
        raise SystemExit(2) from exc
