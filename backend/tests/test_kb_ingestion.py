from types import SimpleNamespace

from app.services.kb_chunker import compute_content_hash
from app.services.kb_ingestion import (
    _clean_formatted_markdown,
    _normalize_formatter_fields,
    normalize_reference_markdown,
    should_reprocess,
)


def test_should_reprocess_when_raw_text_changes():
    reference = SimpleNamespace(content_hash=compute_content_hash("old text"))
    assert should_reprocess(reference, "new text") is True


def test_should_not_reprocess_when_raw_text_unchanged():
    text = "same text"
    reference = SimpleNamespace(content_hash=compute_content_hash(text))
    assert should_reprocess(reference, text) is False


def test_should_not_reprocess_when_raw_text_not_provided():
    reference = SimpleNamespace(content_hash=compute_content_hash("text"))
    assert should_reprocess(reference, None) is False


def test_normalize_removes_empty_wrapper_heading():
    markdown = normalize_reference_markdown(
        "# Intro\n\nBody.\n\n# Q&A\n\n## Q1: Question?\n\nAnswer.\n"
    )
    assert "# Q&A" not in markdown
    assert "# Q1: Question?" in markdown
    assert "Answer." in markdown
    # Promoted out of the empty wrapper — top-level, not nested under Intro.
    from app.services.kb_chunker import chunk_markdown

    paths = [" > ".join(c.heading_path) for c in chunk_markdown(markdown)]
    assert "Q1: Question?" in paths
    assert all(not p.startswith("Intro > Q1") for p in paths)

def test_normalize_promotes_plain_q_labels():
    markdown = normalize_reference_markdown("Q1: Can I get a discount?\n\nNo.\n")
    assert "## Q1: Can I get a discount?" in markdown


def test_normalize_strips_heading_decoration_in_fallback():
    # Fallback runs on raw_text that may already carry decorated markdown headings.
    markdown = normalize_reference_markdown("# ***Background:***\n\nBody.\n")
    assert "# Background:" in markdown
    assert "***" not in markdown


def test_clean_formatted_markdown_strips_llm_empty_wrapper():
    # The LLM output path must strip an empty "# Q&A" wrapper and promote the
    # questions to top level, even though the model produced the wrapper.
    from app.services.kb_chunker import chunk_markdown

    llm_markdown = (
        "# Introduction\n\nOverview.\n\n"
        "# Q&A\n\n## Q1: Can I get a discount?\n\nNo.\n\n## Q2: Any proof?\n\nYes.\n"
    )
    cleaned = _clean_formatted_markdown(llm_markdown)
    assert "# Q&A" not in cleaned

    paths = [" > ".join(c.heading_path) for c in chunk_markdown(cleaned)]
    assert "Q1: Can I get a discount?" in paths
    assert "Q2: Any proof?" in paths
    # No lingering "Q&A" ancestry on any chunk.
    assert all("Q&A" not in p for p in paths)


def test_clean_formatted_markdown_strips_heading_decoration():
    cleaned = _clean_formatted_markdown("# ***Background:***\n\nBody.\n\n# **Notes**\n\nMore.")
    assert "# Background:" in cleaned
    assert "# Notes" in cleaned
    assert "***" not in cleaned


def test_normalize_formatter_fields_applies_cleaner():
    # _normalize_formatter_fields is the single funnel for parsed LLM output;
    # it must unescape newlines AND run the structural cleaner.
    fields = _normalize_formatter_fields(
        "A short summary.",
        "# Intro\\n\\nBody.\\n\\n# Q&A\\n\\n## Q1: Q?\\n\\nA.",
    )
    assert "# Q&A" not in fields["markdown"]
    assert "# Q1: Q?" in fields["markdown"]
