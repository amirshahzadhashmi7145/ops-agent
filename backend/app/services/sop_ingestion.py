import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.resource import Resource
from app.models.sop import SopDocument, SopProcess, SopProcessChunk, SopProcessingStatus
from app.services.embeddings.factory import get_embedding_provider
from app.services.llm.base import ChatMessage
from app.services.llm.factory import get_llm_provider
from app.services.llm_json import parse_json_object

logger = logging.getLogger(__name__)

MENTION_PATTERN = re.compile(r"@\s*([a-zA-Z0-9_-]+)")
BARE_TOOL_PATTERN = re.compile(r"\b(?:call|use|invoke|run)\s+([a-z][a-z0-9_]{2,})\b", re.IGNORECASE)

EXTRACT_PROMPT = """You extract executable SOP processes from an operations document.

The source may be messy — numbered lists, bullets, paragraphs, markdown headings, or free-form prose.
Infer structure even when the writer does not follow a strict template.

Return ONLY one JSON object with keys:
- summary: 2-3 sentence overview of the SOP document
- processes: array of processes

Each process object:
- process_key: snake_case id
- title: short title
- description: what this process does
- trigger_phrases: array of natural language phrases a user might say
- steps: ordered array of step objects
- tools: array of tool call names used (resource names without @)

Each step object:
- id: snake_case
- type: one of ask_user | call_tool | confirm | inform
- instruction: what the agent should do
- tool: optional resource tool name (for call_tool steps)
- inputs: optional object of input hints

Rules:
- Prefer tool names that appear as @mentions (also accept bare tool_name if clearly a tool).
- Normalize mentions: strip leading @, trim whitespace, keep snake_case / kebab names as written.
- Split distinct workflows into separate processes (use headings, blank lines, or topic shifts).
- Preserve order of steps as best as you can.
- If steps are narrative, still emit ask_user / call_tool / confirm / inform steps.
- Do not invent tools that are not mentioned or clearly needed.
- Escape newlines in JSON strings as \\n.
- No markdown fences, no prose outside JSON.
"""


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_mentions(text: str) -> list[str]:
    names = set(MENTION_PATTERN.findall(text))
    names.update(BARE_TOOL_PATTERN.findall(text))
    return sorted({name.strip().lstrip("@") for name in names if name.strip()})


def _normalize_tool_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.strip().lstrip("@").lower()).strip("_")


def count_processes(db: Session, document_id: uuid.UUID) -> int:
    return db.query(SopProcess).filter(SopProcess.document_id == document_id).count()


def should_reprocess(document: SopDocument, raw_text: str) -> bool:
    return document.content_hash != compute_content_hash(raw_text)


def _build_chunk_content(process: dict) -> str:
    steps = process.get("steps") or []
    step_lines = []
    for step in steps:
        tool = step.get("tool")
        line = f"- [{step.get('type', 'inform')}] {step.get('instruction', '')}"
        if tool:
            line += f" (tool: {tool})"
        step_lines.append(line)
    triggers = ", ".join(process.get("trigger_phrases") or [])
    tools = ", ".join(process.get("tools") or [])
    return "\n".join(
        [
            process.get("title", ""),
            process.get("description", ""),
            f"Triggers: {triggers}",
            f"Tools: {tools}",
            "Steps:",
            *step_lines,
        ]
    )


def _normalize_tools(process: dict, mentioned: set[str]) -> list[str]:
    """Collect the normalized tool names a process needs, from its own ``tools``
    list and its ``call_tool`` steps. If the process lists none, fall back to the
    document-wide @mentions. We take the UNION (never an intersection) so a valid
    tool the author referenced without an @ is not silently dropped."""
    tools: set[str] = set()
    for name in process.get("tools") or []:
        if isinstance(name, str) and name.strip():
            tools.add(_normalize_tool_name(name))
    for step in process.get("steps") or []:
        tool = step.get("tool")
        if isinstance(tool, str) and tool.strip():
            normalized = _normalize_tool_name(tool)
            tools.add(normalized)
            step["tool"] = normalized
    if not tools and mentioned:
        return sorted({_normalize_tool_name(name) for name in mentioned})
    return sorted(tools)


async def extract_processes(raw_text: str) -> dict:
    llm = get_llm_provider()
    response = await llm.chat(
        [
            ChatMessage(role="system", content=EXTRACT_PROMPT),
            ChatMessage(role="user", content=raw_text),
        ],
        tool_choice="none",
        max_tokens=settings.kb_format_max_tokens,
        temperature=settings.kb_format_temperature,
    )
    content = (response.content or "").strip()
    parsed = parse_json_object(content)
    if parsed is None:
        raise ValueError("SOP formatter returned no parseable JSON object")
    return parsed


def run_ingestion_task(document_id: uuid.UUID, *, force: bool = False) -> None:
    db = SessionLocal()
    try:
        document = db.get(SopDocument, document_id)
        if not document or not document.active:
            return

        document.processing_status = SopProcessingStatus.formatting
        document.processing_error = None
        db.commit()

        import asyncio

        extracted = asyncio.run(extract_processes(document.raw_text))

        mentioned = set(extract_mentions(document.raw_text))
        # Map normalized name -> real resource name so tool binding is case/format
        # tolerant and the stored tools are the exact names the runtime matches.
        active_by_norm = {
            _normalize_tool_name(row.name): row.name
            for row in db.query(Resource).filter(Resource.active.is_(True)).all()
        }

        processes = extracted.get("processes") or []
        warnings: list[str] = []
        normalized_processes: list[dict] = []
        for index, process in enumerate(processes):
            label = process.get("title") or process.get("process_key") or f"Process {index + 1}"
            bound: list[str] = []
            for name in _normalize_tools(process, mentioned):
                actual = active_by_norm.get(name)
                if actual:
                    if actual not in bound:
                        bound.append(actual)
                else:
                    # Unknown tool: warn and DROP it so the runtime never locks the
                    # SOP to a tool that does not exist (which would stall the flow).
                    warnings.append(f"{label}: unknown tool '{name}' (ignored)")
            # Remap step tools to the real resource name so the steps shown to the
            # model and the allowed-tool list always agree.
            steps = process.get("steps") or []
            for step in steps:
                if isinstance(step, dict):
                    step_tool = step.get("tool")
                    if isinstance(step_tool, str) and step_tool.strip():
                        step["tool"] = active_by_norm.get(_normalize_tool_name(step_tool), step_tool)
            normalized_processes.append(
                {
                    "process_key": process.get("process_key") or f"process_{index + 1}",
                    "title": process.get("title") or f"Process {index + 1}",
                    "description": process.get("description") or "",
                    "trigger_phrases": process.get("trigger_phrases") or [],
                    "steps": steps,
                    "tools": bound,
                    "sort_order": index,
                }
            )

        document.summary = extracted.get("summary")
        document.markdown = document.raw_text
        document.tool_warnings = warnings
        document.processing_status = SopProcessingStatus.indexing
        db.commit()

        # Replace processes + chunks
        existing = db.query(SopProcess).filter(SopProcess.document_id == document.id).all()
        for row in existing:
            db.delete(row)
        db.flush()

        embedder = get_embedding_provider()
        for process_data in normalized_processes:
            process = SopProcess(
                document_id=document.id,
                process_key=process_data["process_key"],
                title=process_data["title"],
                description=process_data["description"],
                trigger_phrases=process_data["trigger_phrases"],
                steps=process_data["steps"],
                tools=process_data["tools"],
                sort_order=process_data["sort_order"],
            )
            db.add(process)
            db.flush()
            content = _build_chunk_content(process_data)
            vector = embedder.embed_documents([content])[0]
            db.add(
                SopProcessChunk(
                    process_id=process.id,
                    content=content,
                    embedding=vector,
                )
            )

        document.embedding_model = embedder.model_name
        document.processing_status = SopProcessingStatus.ready
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("SOP ingestion failed for %s", document_id)
        # Roll back any partial delete/insert from the replace block so the failure
        # marker is written cleanly and old processes are not left half-replaced.
        db.rollback()
        document = db.get(SopDocument, document_id)
        if document:
            document.processing_status = SopProcessingStatus.failed
            document.processing_error = str(exc)
            db.commit()
    finally:
        db.close()
