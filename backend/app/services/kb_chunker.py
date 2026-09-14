import hashlib
import re
from dataclasses import dataclass

HEADER_PATTERN = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
DEFAULT_MAX_CHARS = 1500
DEFAULT_OVERLAP = 200


@dataclass
class MarkdownChunk:
    chunk_index: int
    heading_path: list[str]
    content: str


def compute_content_hash(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def _split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [part for part in parts if part]


def chunk_markdown(
    markdown: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[MarkdownChunk]:
    text = markdown.strip()
    if not text:
        return []

    matches = list(HEADER_PATTERN.finditer(text))
    if not matches:
        sections = [(["Document"], text)]
    else:
        sections: list[tuple[list[str], str]] = []
        heading_stack: list[tuple[int, str]] = []

        # Capture any content before the first heading so it is never dropped
        # from the index (e.g. an intro/overview paragraph the formatter left
        # un-headed). Without this, leading content is silently lost.
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append((["Overview"], preamble))

        for index, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            heading_path = [item[1] for item in heading_stack]

            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            # Skip empty wrapper headings (e.g. "# Q&A" with only child headings after it).
            if not body:
                continue
            section_text = f"{'#' * level} {title}\n\n{body}".strip()
            sections.append((heading_path, section_text))

    chunks: list[MarkdownChunk] = []
    chunk_index = 0
    for heading_path, section_text in sections:
        for part in _split_long_text(section_text, max_chars, overlap):
            chunks.append(
                MarkdownChunk(
                    chunk_index=chunk_index,
                    heading_path=heading_path,
                    content=part,
                )
            )
            chunk_index += 1

    return chunks
