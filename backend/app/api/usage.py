from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.usage.semantic_cache import clear_semantic_cache
from app.services.usage.stats import usage_stats

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats")
def get_usage_stats(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
) -> dict:
    return usage_stats(db, days=days)


@router.post("/semantic-cache/clear")
def clear_usage_semantic_cache(db: Session = Depends(get_db)) -> dict:
    deleted = clear_semantic_cache(db)
    return {"ok": True, "deleted": deleted}
