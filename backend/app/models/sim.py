import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SimSubscriptionStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    past_due = "past_due"


class SimDeviceStatus(str, enum.Enum):
    active = "active"
    return_requested = "return_requested"
    returned = "returned"
    replaced = "replaced"


class SimOrderChannel(str, enum.Enum):
    shopify = "shopify"
    amazon = "amazon"


class SimReturnStatus(str, enum.Enum):
    none = "none"
    return_in_progress = "return_in_progress"
    returned = "returned"


class SimRefundStatus(str, enum.Enum):
    none = "none"
    fully_refunded = "fully_refunded"


class SimFulfillmentStatus(str, enum.Enum):
    unfulfilled = "unfulfilled"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class SimCustomer(Base):
    __tablename__ = "sim_customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions: Mapped[list["SimSubscription"]] = relationship(back_populates="customer")
    devices: Mapped[list["SimDevice"]] = relationship(back_populates="customer")
    orders: Mapped[list["SimOrder"]] = relationship(back_populates="customer")


class SimSubscription(Base):
    __tablename__ = "sim_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sim_customers.id", ondelete="CASCADE"), nullable=False
    )
    plan_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[SimSubscriptionStatus] = mapped_column(
        ENUM(SimSubscriptionStatus, name="simsubscriptionstatus", create_type=False),
        nullable=False,
        default=SimSubscriptionStatus.active,
    )
    monthly_price_usd: Mapped[str] = mapped_column(String(32), nullable=False, default="9.99")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[SimCustomer] = relationship(back_populates="subscriptions")


class SimDevice(Base):
    __tablename__ = "sim_devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sim_customers.id", ondelete="CASCADE"), nullable=False
    )
    serial_number: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[SimDeviceStatus] = mapped_column(
        ENUM(SimDeviceStatus, name="simdevicestatus", create_type=False),
        nullable=False,
        default=SimDeviceStatus.active,
    )
    purchase_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    return_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[SimCustomer] = relationship(back_populates="devices")
    profile: Mapped["SimDeviceProfile | None"] = relationship(back_populates="device", uselist=False)


class SimDeviceProfile(Base):
    __tablename__ = "sim_device_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sim_devices.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    segment: Mapped[str] = mapped_column(String(32), nullable=False, default="consumer")
    camera_family: Mapped[str] = mapped_column(String(32), nullable=False, default="connect")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    lookup_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    classic_diagnostic_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    health_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sim_triage_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sim_data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    device: Mapped[SimDevice] = relationship(back_populates="profile")


class SimOrder(Base):
    __tablename__ = "sim_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sim_customers.id", ondelete="CASCADE"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    channel: Mapped[SimOrderChannel] = mapped_column(
        ENUM(SimOrderChannel, name="simorderchannel", create_type=False),
        nullable=False,
        default=SimOrderChannel.shopify,
    )
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    order_date: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")
    delivery_date: Mapped[str] = mapped_column(String(32), nullable=False)
    fulfillment_status: Mapped[SimFulfillmentStatus] = mapped_column(
        ENUM(SimFulfillmentStatus, name="simfulfillmentstatus", create_type=False),
        nullable=False,
        default=SimFulfillmentStatus.unfulfilled,
    )
    delivery_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deliver_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipping_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_city: Mapped[str] = mapped_column(String(128), nullable=False)
    shipping_state: Mapped[str] = mapped_column(String(64), nullable=False)
    shipping_postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    shipping_country: Mapped[str] = mapped_column(String(64), nullable=False, default="US")
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    return_status: Mapped[SimReturnStatus] = mapped_column(
        ENUM(SimReturnStatus, name="simreturnstatus", create_type=False),
        nullable=False,
        default=SimReturnStatus.none,
    )
    refund_status: Mapped[SimRefundStatus] = mapped_column(
        ENUM(SimRefundStatus, name="simrefundstatus", create_type=False),
        nullable=False,
        default=SimRefundStatus.none,
    )
    return_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rma_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[SimCustomer] = relationship(back_populates="orders")


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
