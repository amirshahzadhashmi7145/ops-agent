import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sim import OutboundMessage

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageListItem(BaseModel):
    id: uuid.UUID
    from_address: str
    to_address: str
    subject: str
    related_entity_type: str | None
    related_entity_id: str | None
    read: bool
    created_at: datetime
    message_kind: str | None = None

    model_config = {"from_attributes": True}


class MessageDetail(MessageListItem):
    body: str
    metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[MessageListItem])
def list_messages(db: Session = Depends(get_db)) -> list[MessageListItem]:
    rows = db.query(OutboundMessage).order_by(OutboundMessage.created_at.desc()).all()
    return [
        MessageListItem(
            id=row.id,
            from_address=row.from_address,
            to_address=row.to_address,
            subject=row.subject,
            related_entity_type=row.related_entity_type,
            related_entity_id=row.related_entity_id,
            read=row.read,
            created_at=row.created_at,
            message_kind=(row.message_metadata or {}).get("message_kind"),
        )
        for row in rows
    ]


@router.get("/{message_id}", response_model=MessageDetail)
def get_message(message_id: uuid.UUID, db: Session = Depends(get_db)) -> MessageDetail:
    message = db.get(OutboundMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if not message.read:
        message.read = True
        db.commit()
        db.refresh(message)
    return MessageDetail(
        id=message.id,
        from_address=message.from_address,
        to_address=message.to_address,
        subject=message.subject,
        body=message.body,
        related_entity_type=message.related_entity_type,
        related_entity_id=message.related_entity_id,
        read=message.read,
        created_at=message.created_at,
        metadata=message.message_metadata,
    )


@router.delete("", status_code=204)
def clear_messages(db: Session = Depends(get_db)) -> None:
    db.query(OutboundMessage).delete()
    db.commit()
