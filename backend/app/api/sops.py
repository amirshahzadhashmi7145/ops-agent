import uuid

import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.sop import SopCategory, SopDocument, SopProcessingStatus
from app.schemas.sop import (
    SopCategoryCreate,
    SopCategoryResponse,
    SopDocumentCreate,
    SopDocumentEnabledUpdate,
    SopDocumentListItem,
    SopDocumentResponse,
    SopDocumentUpdate,
    SopProcessResponse,
)
from app.services.sop_ingestion import (
    compute_content_hash,
    count_processes,
    run_ingestion_task,
    should_reprocess,
)

router = APIRouter(prefix="/sops", tags=["sops"])


def get_user_email(request: Request) -> str:
    return request.headers.get("X-Nexar-User", settings.dev_user_email)


def _document_or_404(db: Session, document_id: uuid.UUID) -> SopDocument:
    document = (
        db.query(SopDocument)
        .options(joinedload(SopDocument.category), joinedload(SopDocument.processes))
        .filter(SopDocument.id == document_id)
        .first()
    )
    if not document or not document.active:
        raise HTTPException(status_code=404, detail="SOP document not found")
    return document


def _to_list_item(db: Session, document: SopDocument) -> SopDocumentListItem:
    return SopDocumentListItem(
        id=document.id,
        title=document.title,
        category_id=document.category_id,
        category_slug=document.category.slug if document.category else None,
        category_name=document.category.name if document.category else None,
        summary=document.summary,
        enabled=document.enabled,
        processing_status=document.processing_status.value,
        processing_error=document.processing_error,
        process_count=count_processes(db, document.id),
        tool_warnings=document.tool_warnings,
        updated_at=document.updated_at,
    )


def _to_response(db: Session, document: SopDocument) -> SopDocumentResponse:
    processes = sorted(document.processes or [], key=lambda p: p.sort_order)
    return SopDocumentResponse(
        id=document.id,
        title=document.title,
        category_id=document.category_id,
        category_slug=document.category.slug if document.category else None,
        category_name=document.category.name if document.category else None,
        raw_text=document.raw_text,
        summary=document.summary,
        markdown=document.markdown,
        content_hash=document.content_hash,
        enabled=document.enabled,
        processing_status=document.processing_status.value,
        processing_error=document.processing_error,
        tool_warnings=document.tool_warnings,
        embedding_model=document.embedding_model,
        process_count=len(processes),
        processes=[
            SopProcessResponse(
                id=p.id,
                process_key=p.process_key,
                title=p.title,
                description=p.description,
                trigger_phrases=p.trigger_phrases or [],
                steps=p.steps or [],
                tools=p.tools or [],
                sort_order=p.sort_order,
            )
            for p in processes
        ],
        created_by=document.created_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _schedule(background_tasks: BackgroundTasks, document_id: uuid.UUID, *, force: bool = False) -> None:
    background_tasks.add_task(run_ingestion_task, document_id, force=force)


def _slugify_category(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "category"


@router.get("/categories", response_model=list[SopCategoryResponse])
def list_categories(db: Session = Depends(get_db)) -> list[SopCategoryResponse]:
    return db.query(SopCategory).order_by(SopCategory.name.asc()).all()


@router.post("/categories", response_model=SopCategoryResponse, status_code=201)
def create_category(payload: SopCategoryCreate, db: Session = Depends(get_db)) -> SopCategory:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")

    base_slug = _slugify_category(name)
    slug = base_slug
    suffix = 2
    while db.query(SopCategory).filter(SopCategory.slug == slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    existing_name = db.query(SopCategory).filter(SopCategory.name.ilike(name)).first()
    if existing_name:
        raise HTTPException(status_code=409, detail="A category with this name already exists")

    category = SopCategory(slug=slug, name=name, description=payload.description or "")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/documents", response_model=list[SopDocumentListItem])
def list_documents(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[SopDocumentListItem]:
    query = (
        db.query(SopDocument)
        .options(joinedload(SopDocument.category))
        .filter(SopDocument.active.is_(True))
    )
    if status:
        try:
            status_enum = SopProcessingStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status filter") from exc
        query = query.filter(SopDocument.processing_status == status_enum)
    if category:
        query = query.join(SopCategory).filter(SopCategory.slug == category)
    if enabled is not None:
        query = query.filter(SopDocument.enabled.is_(enabled))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SopDocument.title.ilike(pattern),
                SopDocument.summary.ilike(pattern),
                SopDocument.raw_text.ilike(pattern),
            )
        )
    rows = query.order_by(SopDocument.updated_at.desc()).all()
    return [_to_list_item(db, row) for row in rows]


@router.post("/documents", response_model=SopDocumentResponse, status_code=201)
def create_document(
    payload: SopDocumentCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SopDocumentResponse:
    category = db.get(SopCategory, payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    document = SopDocument(
        title=payload.title.strip(),
        category_id=payload.category_id,
        raw_text=payload.raw_text,
        content_hash=compute_content_hash(payload.raw_text),
        processing_status=SopProcessingStatus.queued,
        created_by=get_user_email(request),
    )
    db.add(document)
    db.commit()
    _schedule(background_tasks, document.id)
    document = _document_or_404(db, document.id)
    return _to_response(db, document)


@router.get("/documents/{document_id}", response_model=SopDocumentResponse)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> SopDocumentResponse:
    return _to_response(db, _document_or_404(db, document_id))


@router.put("/documents/{document_id}", response_model=SopDocumentResponse)
def update_document(
    document_id: uuid.UUID,
    payload: SopDocumentUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SopDocumentResponse:
    document = _document_or_404(db, document_id)
    category = db.get(SopCategory, payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    reprocess = should_reprocess(document, payload.raw_text) or document.category_id != payload.category_id
    document.title = payload.title.strip()
    document.category_id = payload.category_id
    document.raw_text = payload.raw_text
    document.content_hash = compute_content_hash(payload.raw_text)
    if reprocess:
        document.processing_status = SopProcessingStatus.queued
        document.processing_error = None
    db.commit()
    if reprocess:
        _schedule(background_tasks, document.id, force=True)
    document = _document_or_404(db, document.id)
    return _to_response(db, document)


@router.patch("/documents/{document_id}/enabled", response_model=SopDocumentResponse)
def set_enabled(
    document_id: uuid.UUID,
    payload: SopDocumentEnabledUpdate,
    db: Session = Depends(get_db),
) -> SopDocumentResponse:
    document = _document_or_404(db, document_id)
    document.enabled = payload.enabled
    db.commit()
    document = _document_or_404(db, document.id)
    return _to_response(db, document)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    document = _document_or_404(db, document_id)
    document.active = False
    db.commit()


@router.post("/documents/{document_id}/reprocess", response_model=SopDocumentResponse)
def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SopDocumentResponse:
    document = _document_or_404(db, document_id)
    document.processing_status = SopProcessingStatus.queued
    document.processing_error = None
    db.commit()
    _schedule(background_tasks, document.id, force=True)
    document = _document_or_404(db, document.id)
    return _to_response(db, document)
