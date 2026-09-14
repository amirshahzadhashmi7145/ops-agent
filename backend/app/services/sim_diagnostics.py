import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.sim import SimCustomer, SimDevice, SimDeviceProfile

_PROFILES_PATH = Path(__file__).resolve().parent.parent / "data" / "device_profiles.json"
_PROFILE_CACHE: dict[str, dict] | None = None


def _load_profile_defaults() -> dict[str, dict]:
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        with _PROFILES_PATH.open(encoding="utf-8") as handle:
            _PROFILE_CACHE = json.load(handle)
    return _PROFILE_CACHE


def get_profile_for_serial(db: Session, serial_number: str) -> SimDeviceProfile | None:
    device = db.query(SimDevice).filter(SimDevice.serial_number == serial_number.strip()).first()
    if not device:
        return None
    return db.query(SimDeviceProfile).filter(SimDeviceProfile.device_id == device.id).first()


def profile_payload(profile: SimDeviceProfile | None, serial_number: str) -> dict:
    defaults = _load_profile_defaults().get(serial_number.strip(), {})
    if not profile:
        return defaults
    sim_data = _deep_merge(defaults.get("sim_data") or {}, profile.sim_data_json or {})
    return {
        "segment": profile.segment or defaults.get("segment", "consumer"),
        "camera_family": profile.camera_family or defaults.get("camera_family", "connect"),
        "model": profile.model or defaults.get("model", ""),
        "lookup": _deep_merge(defaults.get("lookup") or {}, profile.lookup_json or {}),
        "classic_diagnostic": profile.classic_diagnostic_json or defaults.get("classic_diagnostic"),
        "health": profile.health_json or defaults.get("health"),
        "sim_triage": defaults.get("sim_triage"),
        "sim_data": sim_data,
    }


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_sim_triage(profile: dict, serial_number: str) -> dict:
    """Compute live SIM triage from merged sim_data (demo state survives tool side-effects)."""
    sim_data = profile.get("sim_data") or {}
    sim = sim_data.get("sim") or {}
    status = str(sim.get("status", "active")).lower()
    last_30d_mb = int(sim.get("last_30d_mb") or 0)
    monthly_cap_mb = int(sim.get("monthly_cap_mb") or 12000)

    if status in {"deactivated", "suspended", "inactive"}:
        return {
            "serial_number": serial_number,
            "conclusion": "sim_inactive",
            "sim_status": status,
            "recommended_action": "reactivate_sim",
            "message": "SIM is deactivated. Reactivate before connectivity troubleshooting.",
        }

    if last_30d_mb >= 25000:
        return {
            "serial_number": serial_number,
            "conclusion": "monthly_cap_exceeded",
            "activity_level": "high",
            "context": {"last_30d_mb": last_30d_mb, "monthly_cap_mb": monthly_cap_mb},
            "recommended_action": "escalate",
            "message": "Monthly data usage exceeds 25GB cap. Escalate for usage review.",
        }

    if last_30d_mb >= 12000 and monthly_cap_mb < 25000:
        return {
            "serial_number": serial_number,
            "conclusion": "monthly_cap_exceeded",
            "activity_level": "high",
            "context": {"last_30d_mb": last_30d_mb, "monthly_cap_mb": monthly_cap_mb},
            "recommended_action": "uplift_25gb",
            "message": "Monthly data usage is high. Uplift cap to 25GB with createLTEQuota25GB.",
        }

    stored = profile.get("sim_triage") or {}
    if stored.get("conclusion") and stored.get("conclusion") != "no_lte_issue":
        return {"serial_number": serial_number, **stored}

    return {
        "serial_number": serial_number,
        "conclusion": "no_lte_issue",
        "activity_level": stored.get("activity_level", "normal"),
        "message": "SIM is active and transmitting normally.",
    }


def find_devices_by_query(db: Session, query: str) -> list[tuple[SimDevice, SimCustomer, dict]]:
    q = query.strip()
    if not q:
        return []

    customers = (
        db.query(SimCustomer)
        .filter(
            (SimCustomer.email.ilike(q))
            | (SimCustomer.phone.ilike(f"%{q}%"))
            | (SimCustomer.full_name.ilike(f"%{q}%"))
        )
        .all()
    )
    devices: list[tuple[SimDevice, SimCustomer, dict]] = []
    seen: set[str] = set()

    device_by_serial = db.query(SimDevice).filter(SimDevice.serial_number.ilike(q)).all()
    for device in device_by_serial:
        customer = db.get(SimCustomer, device.customer_id)
        if customer and device.serial_number not in seen:
            seen.add(device.serial_number)
            profile = get_profile_for_serial(db, device.serial_number)
            devices.append((device, customer, profile_payload(profile, device.serial_number)))

    for customer in customers:
        for device in db.query(SimDevice).filter(SimDevice.customer_id == customer.id).all():
            if device.serial_number in seen:
                continue
            seen.add(device.serial_number)
            profile = get_profile_for_serial(db, device.serial_number)
            devices.append((device, customer, profile_payload(profile, device.serial_number)))

    return devices


def build_lookup_response(device: SimDevice, customer: SimCustomer, profile: dict) -> dict:
    lookup = profile.get("lookup") or {}
    return {
        "serial_number": device.serial_number,
        "model": profile.get("model") or device.model,
        "segment": profile.get("segment", "consumer"),
        "camera_family": profile.get("camera_family", "connect"),
        "customer_name": customer.full_name,
        "customer_email": customer.email,
        "customer_phone": customer.phone,
        "warranty": lookup.get("warranty", {}),
        "subscription": lookup.get("subscription", {}),
        "rear_camera": lookup.get("rear_camera", {}),
        "order_number": lookup.get("order_number"),
        "purchase_date": device.purchase_date,
    }


def merge_classic_flags(devices: list[tuple[SimDevice, SimCustomer, dict]]) -> dict:
    flags: dict = {}
    paired_values: list[bool] = []
    for _, _, profile in devices:
        diag = profile.get("classic_diagnostic")
        if not diag:
            continue
        paired_values.append(bool(diag.get("camera_paired")))
        for key, value in diag.items():
            if key == "camera_paired":
                continue
            if value in (True, False) and value:
                flags[key] = value
            elif isinstance(value, (int, float)) and value:
                flags[key] = value
            elif isinstance(value, str) and value:
                flags[key] = value
    if paired_values:
        flags["camera_paired"] = all(paired_values)
    return {
        "found": bool(flags) or bool(devices),
        "devices_checked": len(devices),
        "flags": flags,
        "classic_diagnostic": flags,
    }
