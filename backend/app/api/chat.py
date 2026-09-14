import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.conversation import Conversation, Message, MessageRole
from app.models.resource import Resource
from app.schemas.chat import ChatStreamRequest, ConversationCreate, ConversationDetail, ConversationListItem
from app.services.agent_runtime import run_agent_turn

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_email(request: Request) -> str:
    return request.headers.get("X-Nexar-User", settings.dev_user_email)


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


@router.get("/conversations", response_model=list[ConversationListItem])
def list_conversations(
    request: Request,
    db: Session = Depends(get_db),
) -> list[ConversationListItem]:
    user_email = get_user_email(request)
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_email == user_email)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return conversations


@router.post("/conversations", response_model=ConversationDetail)
def create_conversation(
    payload: ConversationCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    user_email = get_user_email(request)
    conversation = Conversation(user_email=user_email, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[],
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    user_email = get_user_email(request)
    conversation = _conversation_or_404(db, conversation_id, user_email)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


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
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    prior_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
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
    if conversation.title == "New chat":
        conversation.title = _title_from_message(message_text)
    db.commit()
    db.refresh(user_message)

    async def event_stream():
        final_content = ""
        pipeline_trace: list = []
        try:
            async for event in run_agent_turn(
                user_message=message_text,
                history=history,
                resources=resources,
                user_email=user_email,
                db=db,
            ):
                if event.get("type") == "final_answer":
                    final_content = event.get("content", "")
                    pipeline_trace = event.get("pipeline_trace", [])
                yield json.dumps(event) + "\n"
        except Exception:  # noqa: BLE001
            # Log the real error server-side; never leak raw exception detail to the client.
            logger.exception("Chat turn failed for conversation %s", conversation.id)
            friendly = "Sorry, something went wrong while processing your request. Please try again."
            yield json.dumps({"type": "error", "message": friendly}) + "\n"
            final_content = friendly
            pipeline_trace = [{"type": "error", "message": friendly}]

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=final_content or (
                "Sorry, I couldn't put together a response just now. Please try again."
            ),
            pipeline_trace=pipeline_trace,
        )
        db.add(assistant_message)
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(assistant_message)

        yield json.dumps(
            {
                "type": "done",
                "conversation_id": str(conversation.id),
                "message_id": str(assistant_message.id),
            }
        ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
