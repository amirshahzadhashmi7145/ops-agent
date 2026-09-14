import json
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.kb import KbChunk, KbProcessingStatus, KbReference
from app.services.embeddings.factory import get_embedding_provider
from app.services.kb_chunker import chunk_markdown, compute_content_hash
from app.services.llm.base import ChatMessage
from app.services.llm.factory import get_llm_provider
from app.services.llm_json import (
    _escape_control_chars_in_json_strings,
    _extract_outer_json_object,
    _unwrap_fenced_json,
)

logger = logging.getLogger(__name__)

FORMAT_PROMPT = """You are a knowledge-base formatter. Convert the user's reference text into clean, well-structured markdown for indexing and review.

Your goal: break the content into clear, self-contained sections, each under its own markdown heading, so any single topic can be retrieved on its own. Use your judgment to find the natural sections — you have latitude in how you organize, as long as every fact is preserved and every part of the text lives under a heading.

Identifying sections (this is the most important part):
- Give EVERY distinct topic or labeled section its own heading, even when the source uses no markdown formatting at all.
- Recognize INLINE lead-in labels: a short title followed by its content on the same line or in the same paragraph. Pull the label out as its own heading with its content underneath. For example, text beginning "Background: The most common trigger..." becomes:
  "# Background\\n\\nThe most common trigger...".
  Apply this to labels such as Background, Program Status, Quick Reference, Escalation Note, Tone Guidance, Overview, Summary, Notes, and any similar section label that introduces a block of content.
- Treat each FAQ / Q&A item as its own heading (one heading per question), e.g. "# Q1: ...". Never keep a bare "# Q&A" or "# FAQ" wrapper above them.
- Do NOT leave any content before the first heading or trailing after the last heading. Every paragraph, list, and table must sit under some heading.

Structure:
- Prefer a flat structure: make each section a top-level "# " heading. Use "##"/"###" only when the source genuinely nests content under a parent (e.g. sub-points that only make sense within a parent section).
- Keep distinct topics in distinct sections — do not merge separate topics together, and do not drop or reorder content.
- Every heading MUST have real content beneath it. Never output a heading immediately above another heading with nothing in between.
- Preserve tabular/reference material as a proper markdown table (using "|" pipes) OR a clear bulleted list under its heading — whichever keeps the facts clearest. Do not flatten a table into an ambiguous run of lines.

Faithfulness:
- Do NOT paraphrase, invent, or omit facts. Preserve all factual content, including notes, nuances, and action steps.
- You may drop purely decorative formatting, and you may lightly clean up a heading title for clarity, but never change its meaning.

Output:
- Write a concise 3-4 sentence summary of the content.
- Return ONLY ONE strict JSON object with exactly two keys: "summary" and "markdown".
- Escape all newlines inside JSON strings as \\n (never output raw line breaks inside quoted strings).
- Do not wrap the JSON in code fences, and do not include any prose before or after the JSON object.
"""

HEADER_LINE = re.compile(r"^(#{1,6})\s+(.+)$")


def _remove_empty_wrapper_headings(text: str) -> str:
    """
    Drop headings with no body before the next heading, and promote orphaned
    children one level so FAQ items don't nest under an unrelated previous H1.
    """
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        match = HEADER_LINE.match(stripped)
        if not match:
            result.append(lines[i])
            i += 1
            continue

        level = len(match.group(1))
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1

        next_match = HEADER_LINE.match(lines[j].strip()) if j < len(lines) else None
        if next_match and len(next_match.group(1)) > level:
            i = j
            while i < len(lines):
                child_stripped = lines[i].strip()
                child_match = HEADER_LINE.match(child_stripped)
                if child_match:
                    child_level = len(child_match.group(1))
                    if child_level <= level:
                        break
                    if child_level == level + 1:
                        result.append(f"{'#' * level} {child_match.group(2).strip()}")
                        i += 1
                        continue
                result.append(lines[i])
                i += 1
            continue

        result.append(stripped)
        i += 1

    return "\n".join(result)


def normalize_reference_markdown(raw_text: str) -> str:
    """
    Deterministic fallback used only when the LLM formatter fails/truncates.
    Raw user input is never overwritten by this — only processed markdown falls back here.
    """
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _remove_empty_wrapper_headings(text)

    lines = text.split("\n")
    normalized_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if HEADER_LINE.match(stripped):
            normalized_lines.append(stripped)
            continue
        if re.match(r"^Q\d+\s*[:.\-]", stripped, re.IGNORECASE):
            normalized_lines.append(f"## {stripped}")
            continue
        normalized_lines.append(line.rstrip())

    text = "\n".join(normalized_lines)
    text = _strip_heading_decoration(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _unescape_json_string(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _strip_heading_decoration(text: str) -> str:
    """Remove emphasis markers that wrap heading text (e.g. '# ***Title***' →
    '# Title'). The LLM sometimes decorates headings, which then leaks into
    heading_path and the review UI."""
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        match = HEADER_LINE.match(line.strip())
        if match:
            title = match.group(2).strip().strip("*_`").strip()
            out.append(f"{match.group(1)} {title}")
        else:
            out.append(line)
    return "\n".join(out)


def _clean_formatted_markdown(markdown: str) -> str:
    """Structural cleanup applied to the LLM's markdown before it is stored.

    The LLM does not always obey the formatting rules (e.g. it keeps '# Q&A'
    directly above '## Q1', or decorates headings with '***'). Running these
    deterministic passes guarantees a clean structure regardless of LLM
    compliance: collapse blank runs, remove empty wrapper headings (reusing the
    fallback cleaner), and strip decorative emphasis from headings.
    """
    collapsed = re.sub(r"\n{3,}", "\n\n", markdown)
    dewrapped = _remove_empty_wrapper_headings(collapsed)
    return _strip_heading_decoration(dewrapped).strip()


def _normalize_formatter_fields(summary: str, markdown: str) -> dict[str, str]:
    return {
        "summary": _unescape_json_string(summary).strip(),
        "markdown": _clean_formatted_markdown(_unescape_json_string(markdown).strip()),
    }


def _heuristic_summary(markdown: str) -> str:
    compact = re.sub(r"\s+", " ", markdown).strip()
    if len(compact) <= 320:
        return compact
    return compact[:317].rstrip() + "..."


def _parse_loose_json_fields(content: str) -> dict[str, str] | None:
    summary_match = re.search(
        r'"summary"\s*:\s*"(?P<value>.*?)"\s*,\s*"markdown"\s*:',
        content,
        re.DOTALL,
    )
    markdown_match = re.search(
        r'"markdown"\s*:\s*"(?P<value>.*?)(?:"\s*}\s*$|"\s*}\s*)',
        content,
        re.DOTALL,
    )
    if not summary_match or not markdown_match:
        # Truncation case: summary complete, markdown cut off mid-string.
        summary_only = re.search(r'"summary"\s*:\s*"(?P<value>.*?)"', content, re.DOTALL)
        if summary_only:
            return None
        return None
    return _normalize_formatter_fields(summary_match.group("value"), markdown_match.group("value"))


def _parse_formatter_response(content: str) -> dict[str, str] | None:
    unwrapped = _unwrap_fenced_json(content)
    candidates = [unwrapped, _extract_outer_json_object(unwrapped)]

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        for attempt in (candidate, _escape_control_chars_in_json_strings(candidate)):
            try:
                parsed = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            summary = str(parsed.get("summary", "")).strip()
            markdown = str(parsed.get("markdown", "")).strip()
            if summary and markdown:
                return _normalize_formatter_fields(summary, markdown)

    return _parse_loose_json_fields(unwrapped)


def _extract_partial_summary(content: str) -> str | None:
    unwrapped = _unwrap_fenced_json(content)
    match = re.search(r'"summary"\s*:\s*"(?P<value>.*?)"', unwrapped, re.DOTALL)
    if not match:
        return None
    summary = _unescape_json_string(match.group("value")).strip()
    return summary or None


async def format_reference_text(raw_text: str) -> dict[str, str]:
    """
    Send raw user text to the LLM and use ONLY the LLM response for processed markdown.

    User-applied formatting stays in ``raw_text``. Processed ``markdown`` / ``summary``
    come from the model. If the model truncates/fails, fall back to deterministic
    cleanup of the raw text so indexing still succeeds.
    """
    provider = get_llm_provider()
    try:
        response = await provider.chat(
            [
                ChatMessage(role="system", content=FORMAT_PROMPT),
                ChatMessage(role="user", content=raw_text),
            ],
            tools=None,
            tool_choice="none",
            max_tokens=settings.kb_format_max_tokens,
            temperature=settings.kb_format_temperature,
        )
        content = (response.content or "").strip()
        parsed = _parse_formatter_response(content)
        if parsed:
            return parsed

        logger.warning(
            "KB formatter returned unusable JSON; falling back to local normalize. raw=%s",
            content[:400],
        )
        partial_summary = _extract_partial_summary(content)
    except Exception:  # noqa: BLE001
        logger.exception("KB formatter LLM call failed; falling back to local normalize")
        partial_summary = None

    markdown = normalize_reference_markdown(raw_text)
    if not markdown:
        raise ValueError("Reference content is empty after normalization")
    summary = partial_summary or _heuristic_summary(markdown)
    return {"summary": summary, "markdown": markdown}


def _set_status(
    db: Session,
    reference: KbReference,
    status: KbProcessingStatus,
    *,
    error: str | None = None,
) -> None:
    reference.processing_status = status
    reference.processing_error = error
    reference.updated_at = datetime.now(timezone.utc)
    db.commit()


async def process_reference(db: Session, reference_id: uuid.UUID, *, force: bool = False) -> None:
    reference = db.get(KbReference, reference_id)
    if not reference or not reference.active:
        return

    current_hash = compute_content_hash(reference.raw_text)
    if (
        not force
        and reference.processing_status == KbProcessingStatus.ready
        and reference.content_hash == current_hash
        and reference.markdown
    ):
        return

    reference.content_hash = current_hash
    _set_status(db, reference, KbProcessingStatus.formatting)

    try:
        formatted = await format_reference_text(reference.raw_text)
        reference.summary = formatted["summary"]
        reference.markdown = formatted["markdown"]
        reference.updated_at = datetime.now(timezone.utc)
        db.commit()

        _set_status(db, reference, KbProcessingStatus.indexing)
        db.execute(delete(KbChunk).where(KbChunk.reference_id == reference.id))

        chunks = chunk_markdown(reference.markdown)
        embedder = get_embedding_provider()
        texts = []
        for chunk in chunks:
            path = " > ".join(chunk.heading_path) if chunk.heading_path else "Document"
            texts.append(f"{path}\n\n{chunk.content}")
        vectors = embedder.embed_documents(texts) if texts else []

        for chunk, vector in zip(chunks, vectors, strict=True):
            db.add(
                KbChunk(
                    reference_id=reference.id,
                    chunk_index=chunk.chunk_index,
                    heading_path=chunk.heading_path,
                    content=chunk.content,
                    embedding=vector,
                )
            )

        reference.embedding_model = embedder.model_name
        reference.processing_error = None
        reference.processing_status = KbProcessingStatus.ready
        reference.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("KB ingestion failed for reference %s", reference_id)
        db.rollback()
        reference = db.get(KbReference, reference_id)
        if reference:
            _set_status(db, reference, KbProcessingStatus.failed, error=str(exc))


async def run_ingestion_task(reference_id: uuid.UUID, *, force: bool = False) -> None:
    db = SessionLocal()
    try:
        await process_reference(db, reference_id, force=force)
    finally:
        db.close()


def should_reprocess(reference: KbReference, new_raw_text: str | None) -> bool:
    if new_raw_text is None:
        return False
    return compute_content_hash(new_raw_text) != reference.content_hash


def count_chunks(db: Session, reference_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(KbChunk).where(KbChunk.reference_id == reference_id)
        )
        or 0
    )
