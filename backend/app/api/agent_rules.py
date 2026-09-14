import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.agent_rule import AgentRule, AgentRuleCategory
from app.schemas.agent_rules import AgentRuleCreate, AgentRuleResponse, AgentRuleUpdate

router = APIRouter()


def get_user_email(request: Request) -> str:
    return request.headers.get("X-Nexar-User", settings.dev_user_email)


@router.get("/agent-rules", response_model=list[AgentRuleResponse])
def list_agent_rules(db: Session = Depends(get_db)) -> list[AgentRule]:
    rules = (
        db.execute(
            select(AgentRule).order_by(AgentRule.category.asc(), AgentRule.created_at.asc())
        )
        .scalars()
        .all()
    )
    return list(rules)


@router.post("/agent-rules", response_model=AgentRuleResponse, status_code=201)
def create_agent_rule(
    payload: AgentRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> AgentRule:
    rule = AgentRule(
        category=AgentRuleCategory(payload.category),
        content=payload.content.strip(),
        created_by=get_user_email(request),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/agent-rules/{rule_id}", response_model=AgentRuleResponse)
def update_agent_rule(
    rule_id: uuid.UUID,
    payload: AgentRuleUpdate,
    db: Session = Depends(get_db),
) -> AgentRule:
    rule = db.get(AgentRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if payload.category is not None:
        rule.category = AgentRuleCategory(payload.category)
    if payload.content is not None:
        rule.content = payload.content.strip()
    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/agent-rules/{rule_id}", status_code=204)
def delete_agent_rule(rule_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    rule = db.get(AgentRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
