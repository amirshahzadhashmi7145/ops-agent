"""seed demo SOP documents and processes

Revision ID: 007
Revises: 006
Create Date: 2026-07-08
"""

from typing import Sequence, Union
import hashlib
import json
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SUB_TEXT = """# Subscription Operations

## Cancel subscription
When a customer asks to cancel their subscription or stop billing:
1. Ask for the customer email and confirm you have the right account.
2. Call @lookup_customer_by_email to verify the customer exists.
3. Call @list_subscriptions to show active subscriptions.
4. Ask the user which subscription to cancel and get explicit confirmation.
5. Call @cancel_subscription with the subscription_id.
6. Tell the user a confirmation message was written to the Messages outbox.

Triggers: cancel my subscription, stop my subscription, cancel nexar plan

## Create or get subscription
When a customer wants to start a plan or check status:
1. Ask for the customer email.
2. Call @lookup_customer_by_email.
3. Call @list_subscriptions to show current plans.
4. If they want a new plan, confirm plan name then call @create_subscription.
5. Summarize the result for the user.
"""

RETURN_TEXT = """# Device Return Operations

## Return my device
When a customer wants to return a dash cam:
1. Ask for the customer email.
2. Call @lookup_customer_by_email.
3. Call @list_customer_devices and present the devices.
4. Ask which serial number to return and confirm the reason.
5. Optionally call @lookup_device for that serial.
6. After confirmation, call @initiate_return.
7. Tell the user a return confirmation was logged in Messages.

Triggers: return my device, return my dash cam, start an RMA, send device back
"""


def upgrade() -> None:
    conn = op.get_bind()
    cats = conn.execute(sa.text("SELECT id, slug FROM sop_categories")).fetchall()
    by_slug = {row[1]: str(row[0]) for row in cats}
    if "subscription" not in by_slug or "returns" not in by_slug:
        return

    seed_user = "system@nexar.ops"
    docs = [
        (
            by_slug["subscription"],
            "Subscription Handling",
            SUB_TEXT,
            [
                {
                    "process_key": "cancel_subscription",
                    "title": "Cancel subscription",
                    "description": "Verify customer, list plans, confirm, and cancel via internal tools.",
                    "trigger_phrases": [
                        "cancel my subscription",
                        "stop my subscription",
                        "cancel nexar plan",
                    ],
                    "tools": [
                        "lookup_customer_by_email",
                        "list_subscriptions",
                        "cancel_subscription",
                    ],
                    "steps": [
                        {"id": "ask_email", "type": "ask_user", "instruction": "Ask for the customer email"},
                        {"id": "lookup", "type": "call_tool", "instruction": "Verify customer", "tool": "lookup_customer_by_email"},
                        {"id": "list", "type": "call_tool", "instruction": "List subscriptions", "tool": "list_subscriptions"},
                        {"id": "confirm", "type": "confirm", "instruction": "Confirm which subscription to cancel"},
                        {"id": "cancel", "type": "call_tool", "instruction": "Cancel the subscription", "tool": "cancel_subscription"},
                        {"id": "inform", "type": "inform", "instruction": "Confirm cancellation and that a message was logged"},
                    ],
                },
                {
                    "process_key": "create_or_view_subscription",
                    "title": "Create or view subscription",
                    "description": "Look up a customer and create or review subscriptions.",
                    "trigger_phrases": [
                        "create a subscription",
                        "start a plan",
                        "get my subscription",
                    ],
                    "tools": [
                        "lookup_customer_by_email",
                        "list_subscriptions",
                        "create_subscription",
                    ],
                    "steps": [
                        {"id": "ask_email", "type": "ask_user", "instruction": "Ask for the customer email"},
                        {"id": "lookup", "type": "call_tool", "instruction": "Verify customer", "tool": "lookup_customer_by_email"},
                        {"id": "list", "type": "call_tool", "instruction": "List current subscriptions", "tool": "list_subscriptions"},
                        {"id": "create", "type": "call_tool", "instruction": "Create subscription if requested", "tool": "create_subscription"},
                    ],
                },
            ],
        ),
        (
            by_slug["returns"],
            "Return My Device",
            RETURN_TEXT,
            [
                {
                    "process_key": "return_device",
                    "title": "Return my device",
                    "description": "Identify customer devices, confirm, and initiate a return.",
                    "trigger_phrases": [
                        "return my device",
                        "return my dash cam",
                        "start an RMA",
                        "send device back",
                    ],
                    "tools": [
                        "lookup_customer_by_email",
                        "list_customer_devices",
                        "lookup_device",
                        "initiate_return",
                    ],
                    "steps": [
                        {"id": "ask_email", "type": "ask_user", "instruction": "Ask for the customer email"},
                        {"id": "lookup", "type": "call_tool", "instruction": "Verify customer", "tool": "lookup_customer_by_email"},
                        {"id": "list", "type": "call_tool", "instruction": "List devices", "tool": "list_customer_devices"},
                        {"id": "confirm", "type": "confirm", "instruction": "Confirm serial number and return reason"},
                        {"id": "return", "type": "call_tool", "instruction": "Initiate the return", "tool": "initiate_return"},
                        {"id": "inform", "type": "inform", "instruction": "Confirm return started and message logged"},
                    ],
                }
            ],
        ),
    ]

    for category_id, title, raw_text, processes in docs:
        doc_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO sop_documents (id, category_id, title, raw_text, summary, markdown, content_hash, "
                "enabled, processing_status, processing_error, tool_warnings, embedding_model, active, "
                "created_by, created_at, updated_at) VALUES ("
                ":id, :category_id, :title, :raw_text, :summary, :markdown, :content_hash, true, 'ready', NULL, "
                "'[]'::jsonb, 'keyword-fallback', true, :user, now(), now())"
            ),
            {
                "id": doc_id,
                "category_id": category_id,
                "title": title,
                "raw_text": raw_text,
                "summary": f"Demo SOP: {title}",
                "markdown": raw_text,
                "content_hash": _hash(raw_text),
                "user": seed_user,
            },
        )
        for index, process in enumerate(processes):
            process_id = str(uuid.uuid4())
            conn.execute(
                sa.text(
                    "INSERT INTO sop_processes (id, document_id, process_key, title, description, "
                    "trigger_phrases, steps, tools, sort_order, created_at) VALUES ("
                    ":id, :document_id, :process_key, :title, :description, CAST(:trigger_phrases AS jsonb), "
                    "CAST(:steps AS jsonb), CAST(:tools AS jsonb), :sort_order, now())"
                ),
                {
                    "id": process_id,
                    "document_id": doc_id,
                    "process_key": process["process_key"],
                    "title": process["title"],
                    "description": process["description"],
                    "trigger_phrases": json.dumps(process["trigger_phrases"]),
                    "steps": json.dumps(process["steps"]),
                    "tools": json.dumps(process["tools"]),
                    "sort_order": index,
                },
            )
            content = (
                f"{process['title']}\n{process['description']}\n"
                f"Triggers: {', '.join(process['trigger_phrases'])}\n"
                f"Tools: {', '.join(process['tools'])}"
            )
            conn.execute(
                sa.text(
                    "INSERT INTO sop_process_chunks (id, process_id, content, embedding, created_at) "
                    "VALUES (:id, :process_id, :content, NULL, now())"
                ),
                {"id": str(uuid.uuid4()), "process_id": process_id, "content": content},
            )


def downgrade() -> None:
    op.execute("DELETE FROM sop_documents WHERE created_by = 'system@nexar.ops'")
