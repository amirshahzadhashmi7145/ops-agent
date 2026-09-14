import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.kb import KbChunk, KbProcessingStatus, KbReference
from app.schemas.kb import (
    ReferenceCreate,
    ReferenceEnabledUpdate,
    ReferenceListItem,
    ReferenceResponse,
    ReferenceUpdate,
)
from app.services.kb_chunker import compute_content_hash
from app.services.kb_ingestion import count_chunks, run_ingestion_task, should_reprocess

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def get_user_email(request: Request) -> str:
    return request.headers.get("X-Nexar-User", settings.dev_user_email)


def _reference_or_404(db: Session, reference_id: uuid.UUID) -> KbReference:
    reference = db.get(KbReference, reference_id)
    if not reference or not reference.active:
        raise HTTPException(status_code=404, detail="Reference not found")
    return reference


def _to_response(db: Session, reference: KbReference) -> ReferenceResponse:
    return ReferenceResponse(
        id=reference.id,
        title=reference.title,
        raw_text=reference.raw_text,
        summary=reference.summary,
        markdown=reference.markdown,
        content_hash=reference.content_hash,
        source_url=reference.source_url,
        enabled=reference.enabled,
        processing_status=reference.processing_status.value,
        processing_error=reference.processing_error,
        embedding_model=reference.embedding_model,
        chunk_count=count_chunks(db, reference.id),
        created_by=reference.created_by,
        created_at=reference.created_at,
        updated_at=reference.updated_at,
    )


def _schedule_ingestion(background_tasks: BackgroundTasks, reference_id: uuid.UUID, *, force: bool = False) -> None:
    background_tasks.add_task(run_ingestion_task, reference_id, force=force)


@router.get("/references", response_model=list[ReferenceListItem])
def list_references(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[ReferenceListItem]:
    query = db.query(KbReference).filter(KbReference.active.is_(True))

    if status:
        try:
            status_enum = KbProcessingStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status filter") from exc
        query = query.filter(KbReference.processing_status == status_enum)

    if enabled is not None:
        query = query.filter(KbReference.enabled.is_(enabled))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                KbReference.title.ilike(pattern),
                KbReference.summary.ilike(pattern),
                KbReference.raw_text.ilike(pattern),
            )
        )

    return query.order_by(KbReference.updated_at.desc()).all()


@router.post("/references", response_model=ReferenceResponse, status_code=201)
def create_reference(
    payload: ReferenceCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ReferenceResponse:
    reference = KbReference(
        title=payload.title.strip(),
        raw_text=payload.raw_text,
        content_hash=compute_content_hash(payload.raw_text),
        source_url=payload.source_url.strip() if payload.source_url else None,
        processing_status=KbProcessingStatus.queued,
        created_by=get_user_email(request),
    )
    db.add(reference)
    db.commit()
    db.refresh(reference)
    _schedule_ingestion(background_tasks, reference.id)
    return _to_response(db, reference)


@router.get("/references/{reference_id}", response_model=ReferenceResponse)
def get_reference(reference_id: uuid.UUID, db: Session = Depends(get_db)) -> ReferenceResponse:
    reference = _reference_or_404(db, reference_id)
    return _to_response(db, reference)


@router.put("/references/{reference_id}", response_model=ReferenceResponse)
def update_reference(
    reference_id: uuid.UUID,
    payload: ReferenceUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ReferenceResponse:
    reference = _reference_or_404(db, reference_id)

    if payload.title is not None:
        reference.title = payload.title.strip()
    if payload.source_url is not None:
        reference.source_url = payload.source_url.strip() or None

    reprocess = should_reprocess(reference, payload.raw_text)
    if payload.raw_text is not None:
        reference.raw_text = payload.raw_text
        reference.content_hash = compute_content_hash(payload.raw_text)

    if reprocess:
        reference.processing_status = KbProcessingStatus.queued
        reference.processing_error = None

    db.commit()
    db.refresh(reference)

    if reprocess:
        _schedule_ingestion(background_tasks, reference.id)

    return _to_response(db, reference)


@router.patch("/references/{reference_id}/enabled", response_model=ReferenceResponse)
def set_reference_enabled(
    reference_id: uuid.UUID,
    payload: ReferenceEnabledUpdate,
    db: Session = Depends(get_db),
) -> ReferenceResponse:
    reference = _reference_or_404(db, reference_id)
    reference.enabled = payload.enabled
    db.commit()
    db.refresh(reference)
    return _to_response(db, reference)


@router.delete("/references/{reference_id}", status_code=204)
def delete_reference(reference_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    reference = _reference_or_404(db, reference_id)
    reference.active = False
    db.execute(delete(KbChunk).where(KbChunk.reference_id == reference.id))
    db.commit()


@router.post("/references/{reference_id}/reprocess", response_model=ReferenceResponse)
def reprocess_reference(
    reference_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ReferenceResponse:
    reference = _reference_or_404(db, reference_id)
    reference.processing_status = KbProcessingStatus.queued
    reference.processing_error = None
    db.commit()
    db.refresh(reference)
    _schedule_ingestion(background_tasks, reference.id, force=True)
    return _to_response(db, reference)
