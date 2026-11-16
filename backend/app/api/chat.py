import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_user_email
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.models.resource import Resource
from app.schemas.chat import ChatStreamRequest, ConversationCreate, ConversationDetail, ConversationListItem
from app.services.agent_runtime import run_agent_turn

logger = logging.getLogger(__name__)

router = APIRouter()

# Live chats with no activity for this long are treated as ended on read.
LIVE_IDLE = timedelta(hours=2)


def _conversation_or_404(db: Session, conversation_id: uuid.UUID, user_email: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_email != user_email:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _title_from_message(message: str) -> str:
    cleaned = " ".join(message.strip().split())
    if not cleaned:
        return "New chat"
    return cleaned[:60] + ("..." if len(cleaned) > 60 else "")


def _preview_text(content: str | None, limit: int = 140) -> str | None:
    if not content:
        return None
    cleaned = " ".join(content.strip().split())
    if not cleaned:
        return None
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


def _mark_live(conversation: Conversation) -> None:
    conversation.status = ConversationStatus.live
    conversation.ended_at = None


def _mark_ended(conversation: Conversation, when: datetime | None = None) -> None:
    conversation.status = ConversationStatus.ended
    conversation.ended_at = when or datetime.now(timezone.utc)


def _apply_idle_end(conversation: Conversation, now: datetime) -> bool:
    """End stale live conversations. Returns True if status changed."""
    if conversation.status != ConversationStatus.live:
        return False
    updated = conversation.updated_at
    if updated is not None and updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    if updated is None or updated >= now - LIVE_IDLE:
        return False
    _mark_ended(conversation, when=updated + LIVE_IDLE)
    return True


def _to_list_item(
    conversation: Conversation,
    message_count: int,
    preview: str | None,
) -> ConversationListItem:
    return ConversationListItem(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status.value,
        ended_at=conversation.ended_at,
        message_count=message_count,
        preview=preview,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _to_detail(conversation: Conversation, messages: list[Message]) -> ConversationDetail:
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status.value,
        ended_at=conversation.ended_at,
        message_count=len(messages),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.get("/conversations", response_model=list[ConversationListItem])
def list_conversations(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 50,
    status: str | None = None,
) -> list[ConversationListItem]:
    user_email = get_user_email(request)
    capped = max(1, min(limit, 100))
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_email == user_email)
        .order_by(Conversation.updated_at.desc())
        .limit(capped)
        .all()
    )

    now = datetime.now(timezone.utc)
    dirty = False
    for conversation in conversations:
        if _apply_idle_end(conversation, now):
            dirty = True
    if dirty:
        db.commit()

    if status in {"live", "ended"}:
        conversations = [c for c in conversations if c.status.value == status]

    ids = [c.id for c in conversations]
    counts: dict[uuid.UUID, int] = {}
    previews: dict[uuid.UUID, str | None] = {}
    if ids:
        count_rows = (
            db.query(Message.conversation_id, func.count(Message.id))
            .filter(Message.conversation_id.in_(ids))
            .group_by(Message.conversation_id)
            .all()
        )
        counts = {row[0]: int(row[1]) for row in count_rows}

        # Latest message preview per conversation (by created_at).
        latest_ids = (
            db.query(Message.conversation_id, func.max(Message.created_at).label("latest"))
            .filter(Message.conversation_id.in_(ids))
            .group_by(Message.conversation_id)
            .subquery()
        )
        latest_messages = (
            db.query(Message)
            .join(
                latest_ids,
                (Message.conversation_id == latest_ids.c.conversation_id)
                & (Message.created_at == latest_ids.c.latest),
            )
            .all()
        )
        for message in latest_messages:
            previews[message.conversation_id] = _preview_text(message.content)

    return [
        _to_list_item(conversation, counts.get(conversation.id, 0), previews.get(conversation.id))
        for conversation in conversations
    ]


@router.post("/conversations", response_model=ConversationDetail)
def create_conversation(
    payload: ConversationCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    user_email = get_user_email(request)
    conversation = Conversation(
        user_email=user_email,
        title=payload.title,
        status=ConversationStatus.live,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return _to_detail(conversation, [])


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    user_email = get_user_email(request)
    conversation = _conversation_or_404(db, conversation_id, user_email)
    if _apply_idle_end(conversation, datetime.now(timezone.utc)):
        db.commit()
        db.refresh(conversation)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return _to_detail(conversation, messages)


@router.post("/conversations/{conversation_id}/end", response_model=ConversationDetail)
def end_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    user_email = get_user_email(request)
    conversation = _conversation_or_404(db, conversation_id, user_email)
    _mark_ended(conversation)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return _to_detail(conversation, messages)


@router.post("/conversations/{conversation_id}/reopen", response_model=ConversationDetail)
def reopen_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    user_email = get_user_email(request)
    conversation = _conversation_or_404(db, conversation_id, user_email)
    _mark_live(conversation)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return _to_detail(conversation, messages)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    user_email = get_user_email(request)
    conversation = _conversation_or_404(db, conversation_id, user_email)
    db.delete(conversation)
    db.commit()


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    user_email = get_user_email(request)
    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message is required")

    if payload.conversation_id:
        conversation = _conversation_or_404(db, payload.conversation_id, user_email)
    else:
        conversation = Conversation(
            user_email=user_email,
            title=_title_from_message(message_text),
            status=ConversationStatus.live,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    prior_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(settings.chat_history_max_messages)
        .all()
    )
    prior_messages = list(reversed(prior_messages))
    history = [
        {"role": message.role.value, "content": message.content}
        for message in prior_messages
    ]

    resources = (
        db.execute(
            select(Resource)
            .options(joinedload(Resource.connection))
            .where(Resource.active.is_(True))
            .order_by(Resource.name.asc())
        )
        .unique()
        .scalars()
        .all()
    )

    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=message_text,
        pipeline_trace=[],
    )
    db.add(user_message)
    conversation.updated_at = datetime.now(timezone.utc)
    _mark_live(conversation)
    if conversation.title == "New chat":
        conversation.title = _title_from_message(message_text)
    db.commit()
    db.refresh(user_message)

    conversation_id = conversation.id

    async def event_stream():
        final_content = ""
        pipeline_trace: list = []
        stream_db = SessionLocal()
        try:
            try:
                async for event in run_agent_turn(
                    user_message=message_text,
                    history=history,
                    resources=resources,
                    user_email=user_email,
                    db=stream_db,
                    conversation_id=conversation_id,
                ):
                    if event.get("type") == "final_answer":
                        final_content = event.get("content", "")
                        pipeline_trace = event.get("pipeline_trace", [])
                    yield json.dumps(event) + "\n"
            except Exception:  # noqa: BLE001
                # Log the real error server-side; never leak raw exception detail to the client.
                logger.exception("Chat turn failed for conversation %s", conversation_id)
                friendly = "Sorry, something went wrong while processing your request. Please try again."
                yield json.dumps({"type": "error", "message": friendly}) + "\n"
                final_content = friendly
                pipeline_trace = [{"type": "error", "message": friendly}]

            assistant_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.assistant,
                content=final_content or (
                    "Sorry, I couldn't put together a response just now. Please try again."
                ),
                pipeline_trace=pipeline_trace,
            )
            stream_db.add(assistant_message)
            conv = stream_db.get(Conversation, conversation_id)
            if conv is not None:
                conv.updated_at = datetime.now(timezone.utc)
                _mark_live(conv)
            stream_db.commit()
            stream_db.refresh(assistant_message)

            yield json.dumps(
                {
                    "type": "done",
                    "conversation_id": str(conversation_id),
                    "message_id": str(assistant_message.id),
                }
            ) + "\n"
        finally:
            stream_db.close()

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
