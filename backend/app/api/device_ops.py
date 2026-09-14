import secrets
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sim import OutboundMessage, SimCustomer, SimDevice, SimDeviceProfile, SimOrder
from app.services.sim_diagnostics import (
    _deep_merge,
    _load_profile_defaults,
    build_lookup_response,
    find_devices_by_query,
    get_profile_for_serial,
    merge_classic_flags,
    profile_payload,
    resolve_sim_triage,
)

router = APIRouter(prefix="/sim", tags=["simulation-devices"])

FROM_ADDRESS = "ops-agent@nexar.internal"
RETURN_WINDOW_DAYS = 30


def _queue_message(
    db: Session,
    *,
    to_address: str,
    subject: str,
    body: str,
    related_entity_type: str,
    related_entity_id: str,
    metadata: dict | None = None,
) -> OutboundMessage:
    message = OutboundMessage(
        from_address=FROM_ADDRESS,
        to_address=to_address,
        subject=subject,
        body=body,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        message_metadata=metadata or {},
    )
    db.add(message)
    return message


def _device_or_404(db: Session, serial_number: str) -> tuple[SimDevice, SimCustomer]:
    device = db.query(SimDevice).filter(SimDevice.serial_number == serial_number.strip()).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    customer = db.get(SimCustomer, device.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return device, customer


def _order_by_number(db: Session, order_number: str) -> SimOrder | None:
    cleaned = order_number.strip().lstrip("#").strip()
    return db.query(SimOrder).filter(SimOrder.order_number == cleaned).first()


class ClassicDiagnosticRequest(BaseModel):
    email: str | None = None
    phone: str | None = None


class WarrantyEligibilityRequest(BaseModel):
    email: str
    order_number: str


class ShopifyOrderItemsRequest(BaseModel):
    email: str
    order_number: str


class ShopifyAddress(BaseModel):
    address1: str
    city: str
    province: str
    zip: str
    country: str = "US"
    phone: str | None = None


class ChangeAddressShopifyRequest(BaseModel):
    order_number: str
    customer_email: str
    new_address: ShopifyAddress | dict


class CreateShopifyReplacementRequest(BaseModel):
    camera_model: str
    order_number: str
    issue_summary: str
    serial_number: str
    customer_email: str
    hardware_fault: str
    lines_item_ids: list[str] | str = Field(default_factory=list)
    camera_lens_type: str | None = None
    camera_sd_card_size: str | None = None
    intercom_conversation_id: str | None = None


class CreateShopifyCouponRequest(BaseModel):
    email: str
    discount: int = 25


class AccessoriesCouponRequest(BaseModel):
    email: str


class IntercomMessageRequest(BaseModel):
    contact_id: str | None = None
    email: str | None = None
    message: str


def _merged_sim_data(profile_row: SimDeviceProfile | None, serial_number: str) -> dict:
    defaults = _load_profile_defaults().get(serial_number.strip(), {})
    stored = profile_row.sim_data_json if profile_row else None
    return _deep_merge(defaults.get("sim_data") or {}, stored or {})


@router.get("/devices/lookup")
def get_device_lookup(q: str = Query(...), db: Session = Depends(get_db)) -> dict:
    matches = find_devices_by_query(db, q)
    if not matches:
        return {"found": False, "devices": []}
    devices = [build_lookup_response(device, customer, profile) for device, customer, profile in matches]
    return {"found": True, "devices": devices, "count": len(devices)}


@router.post("/devices/classic/diagnostic")
def get_classic_diagnostic(payload: ClassicDiagnosticRequest, db: Session = Depends(get_db)) -> dict:
    identifier = (payload.email or payload.phone or "").strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="email or phone required")
    matches = find_devices_by_query(db, identifier)
    classic_matches = [(d, c, p) for d, c, p in matches if p.get("camera_family") == "classic"]
    if not classic_matches:
        return {"found": False, "message": "No Classic camera diagnostic data found", "flags": {}}
    result = merge_classic_flags(classic_matches)
    result["identifier"] = identifier
    return result


@router.get("/billing/device-health/{serial_number}")
def get_device_health(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_or_404(db, serial_number)
    profile = profile_payload(get_profile_for_serial(db, serial_number), serial_number)
    health = profile.get("health")
    if not health:
        return {
            "serial_number": device.serial_number,
            "model": profile.get("model") or device.model,
            "camera_family": profile.get("camera_family", "classic"),
            "customer_name": customer.full_name,
            "customer_email": customer.email,
            "status": device.status.value,
            "purchase_date": device.purchase_date,
            "message": "No cloud health data (expected for Classic cameras)",
        }
    return {**health, "customer_name": customer.full_name, "customer_email": customer.email}


@router.get("/devices/{serial_number}/sim-triage")
def get_sim_triage(serial_number: str, db: Session = Depends(get_db)) -> dict:
    _device_or_404(db, serial_number)
    profile = profile_payload(get_profile_for_serial(db, serial_number), serial_number)
    return resolve_sim_triage(profile, serial_number)


@router.get("/devices/{serial_number}/sim-data")
def get_sim_data(serial_number: str, db: Session = Depends(get_db)) -> dict:
    _device_or_404(db, serial_number)
    profile = profile_payload(get_profile_for_serial(db, serial_number), serial_number)
    data = profile.get("sim_data") or {"sim": {"status": "unknown", "last_30d_mb": 0}}
    return {"serial_number": serial_number, **data}


@router.post("/devices/{serial_number}/validate")
def get_validate_serial(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device = db.query(SimDevice).filter(SimDevice.serial_number == serial_number.strip()).first()
    return {"serial_number": serial_number, "registered": device is not None, "valid": device is not None}


@router.post("/devices/{serial_number}/reactivate-sim")
def reactivate_sim(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_or_404(db, serial_number)
    profile_row = get_profile_for_serial(db, serial_number)
    if profile_row:
        merged = _merged_sim_data(profile_row, serial_number)
        sim = dict(merged.get("sim") or {})
        sim["status"] = "active"
        profile_row.sim_data_json = {**merged, "sim": sim}
        profile_row.sim_triage_json = None
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"SIM reactivated for {serial_number}",
        body="Your camera SIM has been reactivated. Please reconnect the camera in the Nexar Connect app.",
        related_entity_type="email",
        related_entity_id=str(device.id),
        metadata={"message_kind": "email", "serial_number": serial_number, "action": "sim_reactivated"},
    )
    db.commit()
    return {"success": True, "serial_number": serial_number, "sim_status": "active"}


@router.post("/devices/{serial_number}/lte-quota-25gb")
def create_lte_quota_25gb(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_or_404(db, serial_number)
    profile_row = get_profile_for_serial(db, serial_number)
    if profile_row:
        merged = _merged_sim_data(profile_row, serial_number)
        sim = dict(merged.get("sim") or {})
        sim["monthly_cap_mb"] = 25000
        profile_row.sim_data_json = {**merged, "sim": sim}
        profile_row.sim_triage_json = None
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Data allowance updated for {serial_number}",
        body="An account adjustment was applied. Your camera should be back online shortly.",
        related_entity_type="email",
        related_entity_id=str(device.id),
        metadata={"message_kind": "email", "serial_number": serial_number, "action": "lte_quota_uplift"},
    )
    db.commit()
    return {"success": True, "serial_number": serial_number, "monthly_cap_mb": 25000}


@router.get("/devices/{serial_number}/order")
def get_device_order(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_or_404(db, serial_number)
    profile = profile_payload(get_profile_for_serial(db, serial_number), serial_number)
    lookup = profile.get("lookup") or {}
    order_number = lookup.get("order_number")
    order = _order_by_number(db, order_number) if order_number else None
    return {
        "serial_number": serial_number,
        "customer_email": customer.email,
        "order_number": order_number,
        "purchase_channel": (lookup.get("warranty") or {}).get("purchase_channel"),
        "delivery_date": (lookup.get("warranty") or {}).get("delivery_date") or device.purchase_date,
        "order_found": order is not None,
        "warranty": lookup.get("warranty", {}),
    }


@router.post("/warranty/eligibility")
def get_warranty_eligibility(payload: WarrantyEligibilityRequest, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, payload.order_number)
    if not order:
        return {"eligible": False, "email_matched": False, "reason": "order_not_found"}
    email_match = order.customer_email.lower() == payload.email.strip().lower()
    if not email_match:
        return {"eligible": False, "email_matched": False, "reason": "email_mismatch"}
    try:
        delivered = date.fromisoformat(order.delivery_date)
    except ValueError:
        delivered = date.today()
    days_since = (date.today() - delivered).days
    eligible = days_since <= 365
    return {
        "eligible": eligible,
        "email_matched": True,
        "delivered_at": order.delivery_date,
        "days_since_delivery": days_since,
        "order_number": order.order_number,
    }


@router.post("/shopify/order-items")
def get_shopify_order_items(payload: ShopifyOrderItemsRequest, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, payload.order_number)
    if not order or order.customer_email.lower() != payload.email.strip().lower():
        return {"found": False, "items": []}
    device = (
        db.query(SimDevice)
        .filter(SimDevice.customer_id == order.customer_id)
        .order_by(SimDevice.created_at.desc())
        .first()
    )
    profile = profile_payload(
        get_profile_for_serial(db, device.serial_number) if device else None,
        device.serial_number if device else "",
    )
    model = profile.get("model") or (device.model if device else "Nexar Dash Cam")
    sd = (profile.get("health") or {}).get("sd_card", {}).get("size_gb", "64 GB")
    item_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{order.order_number}-{model}"))
    return {
        "found": True,
        "order_number": order.order_number,
        "items": [
            {
                "id": item_id,
                "name": model,
                "camera_model": model,
                "camera_lens_type": "road_view",
                "camera_sd_card_size": sd.replace(" GB", "GB"),
                "quantity": 1,
            }
        ],
    }


@router.post("/shopify/change-address")
def change_address_shopify(payload: ChangeAddressShopifyRequest, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, payload.order_number)
    if not order:
        return {"success": False, "message": "Order not found"}
    if order.customer_email.lower() != payload.customer_email.strip().lower():
        return {"success": False, "message": "Email mismatch"}
    addr = payload.new_address if isinstance(payload.new_address, dict) else payload.new_address.model_dump()
    order.shipping_line1 = addr.get("address1", order.shipping_line1)
    order.shipping_city = addr.get("city", order.shipping_city)
    order.shipping_state = addr.get("province", order.shipping_state)
    order.shipping_postal_code = addr.get("zip", order.shipping_postal_code)
    order.shipping_country = addr.get("country", order.shipping_country)
    if addr.get("phone"):
        order.phone = addr["phone"]
    db.commit()
    return {"success": True, "order_number": order.order_number, "updated_address": addr}


@router.post("/shopify/replacement")
def create_shopify_replacement(payload: CreateShopifyReplacementRequest, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, payload.order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    tracking = f"1Z999AA10{secrets.randbelow(10**8):08d}"
    rma_url = f"https://returns.getnexar.com/rma/{order.order_number}"
    _queue_message(
        db,
        to_address=payload.customer_email,
        subject=f"Replacement RMA created for order #{order.order_number}",
        body=(
            f"Faulty hardware replacement initiated for {payload.camera_model} ({payload.serial_number}).\n"
            f"Tracking: {tracking}\nRMA: {rma_url}"
        ),
        related_entity_type="email",
        related_entity_id=str(order.id),
        metadata={
            "message_kind": "email",
            "order_number": order.order_number,
            "tracking_number": tracking,
            "hardware_fault": payload.hardware_fault,
        },
    )
    db.commit()
    return {
        "success": True,
        "order_number": order.order_number,
        "tracking_number": tracking,
        "carrier": "UPS",
        "rma_url": rma_url,
        "product_type": payload.camera_model,
        "updated_shipping_address": f"{order.shipping_line1}, {order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}",
    }


@router.post("/shopify/coupon")
def create_shopify_coupon(payload: CreateShopifyCouponRequest, db: Session = Depends(get_db)) -> dict:
    code = f"NEXAR{payload.discount}-{uuid.uuid4().hex[:8].upper()}"
    _queue_message(
        db,
        to_address=payload.email,
        subject=f"Your {payload.discount}% Nexar discount code",
        body=f"Discount code: {code}\nValid for 60 days on main dashcams at getnexar.com.",
        related_entity_type="email",
        related_entity_id=str(uuid.uuid4()),
        metadata={"message_kind": "email", "discount_code": code, "discount_percent": payload.discount},
    )
    db.commit()
    return {"success": True, "discount_code": code, "discount": payload.discount, "expires_days": 60}


@router.post("/shopify/accessories-coupon")
def get_accessories_coupon(payload: AccessoriesCouponRequest, db: Session = Depends(get_db)) -> dict:
    code = f"ACC-{uuid.uuid4().hex[:10].upper()}"
    _queue_message(
        db,
        to_address=payload.email,
        subject="Your Nexar accessory replacement coupon",
        body=f"Accessory coupon: {code}\nValid 7 days at shop.getnexar.com/collections/accessories",
        related_entity_type="email",
        related_entity_id=str(uuid.uuid4()),
        metadata={"message_kind": "email", "product_discount_code": code},
    )
    db.commit()
    return {"success": True, "product_discount_code": code, "expires_days": 7}


@router.post("/intercom/send-message")
def intercom_send_message_to_contact(payload: IntercomMessageRequest, db: Session = Depends(get_db)) -> dict:
    to_address = payload.email or payload.contact_id or "customer@nexar.invalid"
    _queue_message(
        db,
        to_address=to_address,
        subject="Message from Nexar Support",
        body=payload.message,
        related_entity_type="ticket",
        related_entity_id=str(uuid.uuid4()),
        metadata={"message_kind": "support_ticket", "channel": "intercom"},
    )
    db.commit()
    return {"sent": True, "to": to_address}


@router.get("/devices/profiles")
def list_device_profiles(db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(SimDeviceProfile, SimDevice, SimCustomer)
        .join(SimDevice, SimDeviceProfile.device_id == SimDevice.id)
        .join(SimCustomer, SimDevice.customer_id == SimCustomer.id)
        .order_by(SimDevice.serial_number.asc())
        .all()
    )
    result = []
    for profile, device, customer in rows:
        result.append(
            {
                "serial_number": device.serial_number,
                "customer_email": customer.email,
                "segment": profile.segment,
                "camera_family": profile.camera_family,
                "model": profile.model,
                "sim_triage_conclusion": (profile.sim_triage_json or {}).get("conclusion"),
                "health_score": (profile.health_json or {}).get("summary", {}).get("health_score"),
            }
        )
    return result
