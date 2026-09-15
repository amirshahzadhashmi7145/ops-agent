import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sim import (
    OutboundMessage,
    SimCustomer,
    SimDevice,
    SimDeviceStatus,
    SimFulfillmentStatus,
    SimOrder,
    SimOrderChannel,
    SimRefundStatus,
    SimReturnStatus,
    SimSubscription,
    SimSubscriptionStatus,
)

router = APIRouter(prefix="/sim", tags=["simulation"])

FROM_ADDRESS = "ops-agent@nexar.internal"
RETURN_WINDOW_DAYS = 30
AMAZON_ORDER_PATTERN = re.compile(r"^\d{3}-\d{7}-\d{7}$")
SHOPIFY_ORDER_PATTERN = re.compile(r"^\d{4,8}$")


class CustomerOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    plan_name: str
    status: str
    monthly_price_usd: str
    cancelled_at: datetime | None = None

    model_config = {"from_attributes": True}


class DeviceOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    serial_number: str
    model: str
    status: str
    purchase_date: str | None = None
    return_reason: str | None = None

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    order_number: str
    channel: str
    customer_email: str
    order_date: str
    delivery_date: str
    fulfillment_status: str
    delivery_status: str | None = None
    deliver_by: str | None = None
    tags: list[str] | None = None
    shipping_name: str
    shipping_line1: str
    shipping_line2: str | None = None
    shipping_city: str
    shipping_state: str
    shipping_postal_code: str
    shipping_country: str
    phone: str
    return_status: str
    refund_status: str
    return_reason: str | None = None
    rma_url: str | None = None
    tracking_number: str | None = None

    model_config = {"from_attributes": True}


class CreateSubscriptionBody(BaseModel):
    email: str
    plan_name: str = "Nexar Pro Monthly"
    monthly_price_usd: str = "12.99"


class CancelBody(BaseModel):
    reason: str = "Customer request"


class ReturnBody(BaseModel):
    reason: str = "Customer return"


def _customer_by_email(db: Session, email: str) -> SimCustomer:
    customer = db.query(SimCustomer).filter(SimCustomer.email.ilike(email.strip())).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer not found: {email}")
    return customer


def _normalize_order_number(raw: str) -> str:
    cleaned = raw.strip().lstrip("#").strip()
    return cleaned


def _identify_channel(order_number: str) -> str | None:
    if AMAZON_ORDER_PATTERN.match(order_number):
        return "amazon"
    if SHOPIFY_ORDER_PATTERN.match(order_number):
        return "shopify"
    return None


def _order_by_number(db: Session, order_number: str) -> SimOrder | None:
    normalized = _normalize_order_number(order_number)
    return db.query(SimOrder).filter(SimOrder.order_number == normalized).first()


def _format_shipping_address(order: SimOrder) -> str:
    lines = [
        order.shipping_name,
        order.shipping_line1,
    ]
    if order.shipping_line2:
        lines.append(order.shipping_line2)
    lines.append(f"{order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}")
    lines.append(order.shipping_country)
    return "\n".join(lines)


def _delivery_within_return_window(delivery_date: str) -> bool:
    try:
        delivered = date.fromisoformat(delivery_date)
    except ValueError:
        return False
    return (date.today() - delivered).days <= RETURN_WINDOW_DAYS


def _days_since(date_str: str) -> int | None:
    try:
        start = date.fromisoformat(date_str)
    except ValueError:
        return None
    return (date.today() - start).days


def _order_status_payload(order: SimOrder, customer: SimCustomer | None = None) -> dict:
    customer = customer or order.customer
    return {
        "order_number": order.order_number,
        "email": order.customer_email,
        "customer_name": customer.full_name if customer else "",
        "channel": order.channel.value,
        "order_date": order.order_date,
        "updated_at": order.updated_at.isoformat() if order.updated_at else "",
        "days_since_order": _days_since(order.order_date),
        "fulfillment_status": order.fulfillment_status.value,
        "delivery_status": order.delivery_status or "",
        "tracking_number": order.tracking_number or "",
        "deliver_by": order.deliver_by or "",
        "tags": order.tags or [],
        "shipping_address": _format_shipping_address(order),
        "delivery_date": order.delivery_date,
        "return_status": order.return_status.value if order.return_status != SimReturnStatus.none else "",
        "refund_status": order.refund_status.value if order.refund_status != SimRefundStatus.none else "",
        "rma_url": order.rma_url,
        "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else "",
    }


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


class InvoiceRequest(BaseModel):
    serial_number: str
    months: int = 6


class InvoiceEmailRequest(InvoiceRequest):
    email: str


class PlanChangeRequest(BaseModel):
    serial_number: str


class JiraIssueRequest(BaseModel):
    projectId: str
    issueTypeId: str
    status: str
    summary: str
    description: str
    custom_fields: str | dict


class TicketEscalateRequest(BaseModel):
    queue_parameters: str | dict
    reason: str | None = None


class TicketInternalNoteRequest(BaseModel):
    note: str


class TicketResolveRequest(BaseModel):
    reason: str | None = None


class TicketMessageResponseRequest(BaseModel):
    message: str
    customer_email: str | None = None


class VerifyReturnEligibilityRequest(BaseModel):
    order_number: str
    customer_email: str


class CreateReturnForOrderRequest(BaseModel):
    order_number: str
    customer_email: str
    return_reason: str
    conversation_id: str | None = None


class CancelShopifyOrderRequest(BaseModel):
    email: str
    orderNumber: str
    intercomConversationId: str | None = None


def _device_with_customer(db: Session, serial_number: str) -> tuple[SimDevice, SimCustomer]:
    device = db.query(SimDevice).filter(SimDevice.serial_number == serial_number.strip()).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    customer = db.get(SimCustomer, device.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return device, customer


@router.get("/billing/device-subscription/{serial_number}")
def get_device_subscription(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_with_customer(db, serial_number)
    sub = (
        db.query(SimSubscription)
        .filter(SimSubscription.customer_id == customer.id)
        .order_by(SimSubscription.created_at.desc())
        .first()
    )
    if not sub:
        return {"found": False, "serial_number": serial_number}
    return {
        "found": True,
        "serial_number": serial_number,
        "customer_name": customer.full_name,
        "customer_email": customer.email,
        "subscription_id": str(sub.id),
        "plan_name": sub.plan_name,
        "status": sub.status.value,
        "monthly_price_usd": sub.monthly_price_usd,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
    }


@router.post("/billing/recurly/invoices")
def get_recurly_invoices(payload: InvoiceRequest, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_with_customer(db, payload.serial_number)
    has_email = bool(customer.email)
    _queue_message(
        db,
        to_address=customer.email or "unknown@nexar.invalid",
        subject=f"Invoices sent for {device.serial_number}",
        body=(
            f"Sent the last {payload.months} invoice(s) for serial {device.serial_number} "
            f"to {customer.email or 'N/A'}."
        ),
        related_entity_type="email",
        related_entity_id=str(device.id),
        metadata={"message_kind": "email", "months": payload.months, "serial_number": device.serial_number},
    )
    db.commit()
    return {"emailFound": has_email, "sent": has_email, "months": payload.months}


@router.post("/billing/recurly/email-and-send")
def update_recurly_email_and_send(payload: InvoiceEmailRequest, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_with_customer(db, payload.serial_number)
    customer.email = payload.email.strip()
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Billing email updated and invoices sent ({device.serial_number})",
        body=f"Updated billing email to {customer.email} and sent last {payload.months} invoices.",
        related_entity_type="email",
        related_entity_id=str(device.id),
        metadata={"message_kind": "email", "months": payload.months, "serial_number": device.serial_number},
    )
    db.commit()
    return {"updated": True, "sent": True, "email": customer.email, "months": payload.months}


@router.post("/billing/subscriptions/{serial_number}/to-annual")
def to_annual(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_with_customer(db, serial_number)
    sub = (
        db.query(SimSubscription)
        .filter(SimSubscription.customer_id == customer.id, SimSubscription.status == SimSubscriptionStatus.active)
        .order_by(SimSubscription.created_at.desc())
        .first()
    )
    if not sub:
        return {"success": False, "paymentRequired": False, "message": "No active subscription found"}
    sub.plan_name = "Nexar Annual Plan"
    sub.monthly_price_usd = "95.88"
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Plan change scheduled: Annual ({serial_number})",
        body="Your subscription will switch to annual billing at next renewal.",
        related_entity_type="email",
        related_entity_id=str(sub.id),
        metadata={"message_kind": "email", "serial_number": serial_number},
    )
    db.commit()
    return {"success": True, "paymentRequired": False}


@router.post("/billing/subscriptions/{serial_number}/to-monthly")
def to_monthly(serial_number: str, db: Session = Depends(get_db)) -> dict:
    device, customer = _device_with_customer(db, serial_number)
    sub = (
        db.query(SimSubscription)
        .filter(SimSubscription.customer_id == customer.id)
        .order_by(SimSubscription.created_at.desc())
        .first()
    )
    if not sub:
        return {"success": False, "paymentRequired": False, "message": "No subscription found"}
    sub.plan_name = "Nexar Monthly Plan"
    sub.monthly_price_usd = "9.99"
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Plan change scheduled: Monthly ({serial_number})",
        body="Your subscription will switch to monthly billing at end of current annual term.",
        related_entity_type="email",
        related_entity_id=str(sub.id),
        metadata={"message_kind": "email", "serial_number": serial_number},
    )
    db.commit()
    return {"success": True, "paymentRequired": False}


@router.post("/ops/jira/issues")
def jira_create_issue(payload: JiraIssueRequest, db: Session = Depends(get_db)) -> dict:
    issue_key = f"NX-{int(datetime.now(timezone.utc).timestamp())}"
    _queue_message(
        db,
        to_address="backoffice@nexar.internal",
        subject=f"Jira ticket created: {issue_key} · {payload.summary}",
        body=payload.description,
        related_entity_type="jira",
        related_entity_id=issue_key,
        metadata={
            "message_kind": "jira_ticket",
            "projectId": payload.projectId,
            "issueTypeId": payload.issueTypeId,
            "status": payload.status,
            "summary": payload.summary,
            "custom_fields": payload.custom_fields,
        },
    )
    db.commit()
    return {"issueKey": issue_key, "status": payload.status}


@router.post("/ops/tickets/escalate")
def ticket_escalate(payload: TicketEscalateRequest, db: Session = Depends(get_db)) -> dict:
    _queue_message(
        db,
        to_address="human-agent-queue@nexar.internal",
        subject="Ticket escalated to human queue",
        body=payload.reason or "Escalation requested by SOP.",
        related_entity_type="ticket",
        related_entity_id=str(uuid.uuid4()),
        metadata={"message_kind": "support_ticket", "queue_parameters": payload.queue_parameters},
    )
    db.commit()
    return {"escalated": True}


@router.post("/ops/tickets/internal-note")
def ticket_internal_note(payload: TicketInternalNoteRequest, db: Session = Depends(get_db)) -> dict:
    _queue_message(
        db,
        to_address="internal-notes@nexar.internal",
        subject="Internal ticket note added",
        body=payload.note,
        related_entity_type="ticket_note",
        related_entity_id=str(uuid.uuid4()),
        metadata={"message_kind": "ticket_note"},
    )
    db.commit()
    return {"saved": True}


@router.post("/ops/tickets/resolve")
def ticket_resolve(payload: TicketResolveRequest | None = None, db: Session = Depends(get_db)) -> dict:
    body = payload or TicketResolveRequest()
    reason = body.reason or "Spam or unwanted marketing/voicemail"
    _queue_message(
        db,
        to_address="support-automation@nexar.internal",
        subject="Ticket resolved automatically",
        body=f"Ticket resolved by SOP automation. Reason: {reason}",
        related_entity_type="ticket",
        related_entity_id=str(uuid.uuid4()),
        metadata={"message_kind": "ticket_resolved", "reason": reason},
    )
    db.commit()
    return {"resolved": True, "reason": reason}


@router.post("/ops/tickets/message-response")
def ticket_message_response(payload: TicketMessageResponseRequest, db: Session = Depends(get_db)) -> dict:
    """Identify purchase channel from order number in a customer message."""
    text = payload.message.strip()
    order_match = re.search(r"#?\s*(\d{3}-\d{7}-\d{7}|\d{4,8})", text)
    if not order_match:
        to_address = payload.customer_email or "customer@nexar.invalid"
        _queue_message(
            db,
            to_address=to_address,
            subject="Help us locate your Nexar order",
            body=(
                "To help with your return, please share where you purchased your dash cam "
                "(Nexar shop or Amazon) or your order number.\n\n"
                "Shopify orders look like #346741. Amazon orders look like #114-1536531-8448242."
            ),
            related_entity_type="ticket",
            related_entity_id=str(uuid.uuid4()),
            metadata={"message_kind": "support_ticket", "action": "request_order_info"},
        )
        db.commit()
        return {
            "identified": False,
            "needs_order_number": True,
            "message": "Asked customer for purchase channel or order number.",
        }

    order_number = _normalize_order_number(order_match.group(1))
    channel = _identify_channel(order_number)
    order = _order_by_number(db, order_number)
    if order:
        channel = order.channel.value

    return {
        "identified": True,
        "order_number": order_number,
        "channel": channel,
        "found_in_system": order is not None,
        "amazon_return_url": "https://www.amazon.com/returns" if channel == "amazon" else None,
        "proceed_with_shopify_sop": channel == "shopify",
    }


@router.post("/returns/verify-eligibility")
def verify_return_eligibility(payload: VerifyReturnEligibilityRequest, db: Session = Depends(get_db)) -> dict:
    order_number = _normalize_order_number(payload.order_number)
    order = _order_by_number(db, order_number)
    if not order:
        return {"eligible": False, "reason": "order_not_found", "order_number": order_number}

    if order.channel == SimOrderChannel.amazon:
        return {
            "eligible": False,
            "reason": "amazon_order",
            "order_number": order_number,
            "message": "Amazon orders must be returned through amazon.com/returns",
        }

    if order.customer_email.lower() != payload.customer_email.strip().lower():
        return {"eligible": False, "reason": "email_mismatch", "order_number": order_number}

    if order.return_status in {SimReturnStatus.return_in_progress, SimReturnStatus.returned}:
        return {
            "eligible": False,
            "reason": "already_returned",
            "order_number": order_number,
            "return_status": order.return_status.value,
            "tracking_number": order.tracking_number,
            "rma_url": order.rma_url,
        }

    if not _delivery_within_return_window(order.delivery_date):
        return {
            "eligible": False,
            "reason": "outside_30_days",
            "order_number": order_number,
            "delivery_date": order.delivery_date,
        }

    return {
        "eligible": True,
        "order_number": order_number,
        "customer_email": order.customer_email,
        "delivery_date": order.delivery_date,
    }


@router.get("/returns/orders/{order_number}/shipping")
def get_order_shipping_address_and_phone_number(order_number: str, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_number": order.order_number,
        "shipping_name": order.shipping_name,
        "shipping_address": _format_shipping_address(order),
        "shipping_line1": order.shipping_line1,
        "shipping_line2": order.shipping_line2,
        "shipping_city": order.shipping_city,
        "shipping_state": order.shipping_state,
        "shipping_postal_code": order.shipping_postal_code,
        "shipping_country": order.shipping_country,
        "phone": order.phone,
    }


@router.post("/returns/create")
def create_return_for_order(payload: CreateReturnForOrderRequest, db: Session = Depends(get_db)) -> dict:
    eligibility = verify_return_eligibility(
        VerifyReturnEligibilityRequest(
            order_number=payload.order_number,
            customer_email=payload.customer_email,
        ),
        db,
    )
    if not eligibility.get("eligible"):
        raise HTTPException(status_code=400, detail=eligibility)

    order = _order_by_number(db, payload.order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    tracking_number = f"9434650895206{secrets.randbelow(10**8):08d}"
    rma_url = f"https://returns.getnexar.com/rma/{order.order_number}"
    order.return_status = SimReturnStatus.return_in_progress
    order.return_reason = payload.return_reason
    order.tracking_number = tracking_number
    order.rma_url = rma_url

    customer = db.get(SimCustomer, order.customer_id)
    if customer:
        _queue_message(
            db,
            to_address=order.customer_email,
            subject=f"Return label and instructions for order #{order.order_number}",
            body=(
                f"Your prepaid USPS return label is ready.\n"
                f"RMA: {rma_url}\n"
                f"Tracking: {tracking_number}\n"
                f"Reason: {payload.return_reason}"
            ),
            related_entity_type="email",
            related_entity_id=str(order.id),
            metadata={
                "message_kind": "email",
                "order_number": order.order_number,
                "tracking_number": tracking_number,
                "rma_url": rma_url,
                "conversation_id": payload.conversation_id,
            },
        )

    db.commit()
    return {
        "success": True,
        "order_number": order.order_number,
        "return_reason": payload.return_reason,
        "tracking_number": tracking_number,
        "carrier": "USPS",
        "rma_url": rma_url,
        "confirmation_template": (
            f"✅ Return Request Created Successfully!\n"
            f"Order: #{order.order_number}\n"
            f"Return Reason: {payload.return_reason.replace('_', ' ').title()}\n"
            f"📦 Tracking Number: {tracking_number} (USPS)\n"
            f"You can track your return shipment using the tracking number above.\n\n"
            f"We've also sent a separate email with your return instructions and a link to "
            f"download your prepaid return label. Please print and attach this label to the "
            f"outside of the package containing the items you're returning, then drop it off at "
            f"any nearby USPS location.\n\n"
            f"Once we receive and inspect the returned items, your refund will be processed.\n\n"
            f"Important: If you've already activated your Nexar Connect subscription, please log "
            f"in to your MyNexar portal to cancel the subscription."
        ),
    }


@router.get("/returns/orders/{order_number}/status")
def get_order_status_shopify(order_number: str, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.channel != SimOrderChannel.shopify:
        return {
            "order_number": order.order_number,
            "channel": order.channel.value,
            "message": "Nexar can only manage Shopify orders. Amazon orders must be handled through Amazon directly.",
        }
    customer = db.get(SimCustomer, order.customer_id)
    return _order_status_payload(order, customer)


@router.post("/shipping/orders/cancel")
def cancel_shopify_order(payload: CancelShopifyOrderRequest, db: Session = Depends(get_db)) -> dict:
    order = _order_by_number(db, payload.orderNumber)
    if not order:
        return {"success": False, "message": "Order not found"}
    if order.channel != SimOrderChannel.shopify:
        return {
            "success": False,
            "message": "Only Shopify orders can be cancelled through Nexar. Amazon orders must be handled through Amazon.",
        }
    if order.customer_email.lower() != payload.email.strip().lower():
        return {"success": False, "message": "Email does not match order on file"}
    if order.fulfillment_status == SimFulfillmentStatus.cancelled:
        return {"success": True, "message": "Order was already cancelled"}
    if order.fulfillment_status != SimFulfillmentStatus.unfulfilled:
        return {
            "success": False,
            "message": "Order has already been processed and can no longer be cancelled",
            "fulfillment_status": order.fulfillment_status.value,
        }

    order.fulfillment_status = SimFulfillmentStatus.cancelled
    order.cancelled_at = datetime.now(timezone.utc)
    customer = db.get(SimCustomer, order.customer_id)
    _queue_message(
        db,
        to_address=order.customer_email,
        subject=f"Order #{order.order_number} cancelled",
        body=(
            f"Your order #{order.order_number} has been cancelled. "
            f"A refund will be processed within 7-10 business days."
        ),
        related_entity_type="email",
        related_entity_id=str(order.id),
        metadata={
            "message_kind": "email",
            "order_number": order.order_number,
            "intercom_conversation_id": payload.intercomConversationId,
        },
    )
    db.commit()
    return {
        "success": True,
        "order_number": order.order_number,
        "message": "Order cancelled successfully. Refund within 7-10 business days.",
    }


@router.get("/customers/{email}", response_model=CustomerOut)
def lookup_customer(email: str, db: Session = Depends(get_db)) -> CustomerOut:
    return _customer_by_email(db, email)


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    email: str = Query(...),
    db: Session = Depends(get_db),
) -> list[SubscriptionOut]:
    customer = _customer_by_email(db, email)
    rows = (
        db.query(SimSubscription)
        .filter(SimSubscription.customer_id == customer.id)
        .order_by(SimSubscription.created_at.desc())
        .all()
    )
    return [
        SubscriptionOut(
            id=r.id,
            customer_id=r.customer_id,
            plan_name=r.plan_name,
            status=r.status.value,
            monthly_price_usd=r.monthly_price_usd,
            cancelled_at=r.cancelled_at,
        )
        for r in rows
    ]


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
def create_subscription(payload: CreateSubscriptionBody, db: Session = Depends(get_db)) -> SubscriptionOut:
    customer = _customer_by_email(db, payload.email)
    sub = SimSubscription(
        customer_id=customer.id,
        plan_name=payload.plan_name,
        status=SimSubscriptionStatus.active,
        monthly_price_usd=payload.monthly_price_usd,
    )
    db.add(sub)
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Your {payload.plan_name} subscription is active",
        body=(
            f"Hi {customer.full_name},\n\n"
            f"Your subscription to {payload.plan_name} (${payload.monthly_price_usd}/mo) is now active.\n\n"
            f"— Nexar Ops Agent"
        ),
        related_entity_type="subscription",
        related_entity_id="pending",
        metadata={"plan_name": payload.plan_name},
    )
    db.commit()
    db.refresh(sub)
    # Fix related id on message
    msg = (
        db.query(OutboundMessage)
        .filter(OutboundMessage.related_entity_type == "subscription", OutboundMessage.related_entity_id == "pending")
        .order_by(OutboundMessage.created_at.desc())
        .first()
    )
    if msg:
        msg.related_entity_id = str(sub.id)
        db.commit()
    return SubscriptionOut(
        id=sub.id,
        customer_id=sub.customer_id,
        plan_name=sub.plan_name,
        status=sub.status.value,
        monthly_price_usd=sub.monthly_price_usd,
        cancelled_at=sub.cancelled_at,
    )


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionOut)
def cancel_subscription(
    subscription_id: uuid.UUID,
    payload: CancelBody | None = None,
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    body = payload or CancelBody()
    sub = db.get(SimSubscription, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    customer = db.get(SimCustomer, sub.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if sub.status == SimSubscriptionStatus.cancelled:
        raise HTTPException(status_code=400, detail="Subscription already cancelled")

    sub.status = SimSubscriptionStatus.cancelled
    sub.cancelled_at = datetime.now(timezone.utc)
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Subscription cancelled — {sub.plan_name}",
        body=(
            f"Hi {customer.full_name},\n\n"
            f"Your {sub.plan_name} subscription has been cancelled.\n"
            f"Reason: {body.reason}\n"
            f"Subscription ID: {sub.id}\n\n"
            f"— Nexar Ops Agent"
        ),
        related_entity_type="subscription",
        related_entity_id=str(sub.id),
        metadata={"reason": body.reason, "plan_name": sub.plan_name},
    )
    db.commit()
    db.refresh(sub)
    return SubscriptionOut(
        id=sub.id,
        customer_id=sub.customer_id,
        plan_name=sub.plan_name,
        status=sub.status.value,
        monthly_price_usd=sub.monthly_price_usd,
        cancelled_at=sub.cancelled_at,
    )


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(email: str = Query(...), db: Session = Depends(get_db)) -> list[DeviceOut]:
    customer = _customer_by_email(db, email)
    rows = (
        db.query(SimDevice)
        .filter(SimDevice.customer_id == customer.id)
        .order_by(SimDevice.created_at.desc())
        .all()
    )
    return [
        DeviceOut(
            id=r.id,
            customer_id=r.customer_id,
            serial_number=r.serial_number,
            model=r.model,
            status=r.status.value,
            purchase_date=r.purchase_date,
            return_reason=r.return_reason,
        )
        for r in rows
    ]


@router.get("/devices/{serial_number}", response_model=DeviceOut)
def lookup_device(serial_number: str, db: Session = Depends(get_db)) -> DeviceOut:
    device = db.query(SimDevice).filter(SimDevice.serial_number == serial_number.strip()).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceOut(
        id=device.id,
        customer_id=device.customer_id,
        serial_number=device.serial_number,
        model=device.model,
        status=device.status.value,
        purchase_date=device.purchase_date,
        return_reason=device.return_reason,
    )


@router.post("/devices/{serial_number}/return", response_model=DeviceOut)
def initiate_return(
    serial_number: str,
    payload: ReturnBody | None = None,
    db: Session = Depends(get_db),
) -> DeviceOut:
    body = payload or ReturnBody()
    device = db.query(SimDevice).filter(SimDevice.serial_number == serial_number.strip()).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    customer = db.get(SimCustomer, device.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if device.status in {SimDeviceStatus.return_requested, SimDeviceStatus.returned}:
        raise HTTPException(status_code=400, detail=f"Device already in status: {device.status.value}")

    device.status = SimDeviceStatus.return_requested
    device.return_reason = body.reason
    _queue_message(
        db,
        to_address=customer.email,
        subject=f"Return initiated for {device.model} ({device.serial_number})",
        body=(
            f"Hi {customer.full_name},\n\n"
            f"We have started a return for your {device.model}.\n"
            f"Serial: {device.serial_number}\n"
            f"Reason: {body.reason}\n\n"
            f"A prepaid label will arrive in a follow-up message.\n\n"
            f"— Nexar Ops Agent"
        ),
        related_entity_type="device",
        related_entity_id=str(device.id),
        metadata={"serial_number": device.serial_number, "reason": body.reason},
    )
    db.commit()
    db.refresh(device)
    return DeviceOut(
        id=device.id,
        customer_id=device.customer_id,
        serial_number=device.serial_number,
        model=device.model,
        status=device.status.value,
        purchase_date=device.purchase_date,
        return_reason=device.return_reason,
    )
