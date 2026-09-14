from app.services.kb_chunker import chunk_markdown, compute_content_hash


def test_compute_content_hash_stable():
    text = "Same content"
    assert compute_content_hash(text) == compute_content_hash(text)
    assert compute_content_hash(text) != compute_content_hash("Different")


def test_chunk_markdown_captures_preamble_before_first_heading():
    # Content before the first heading must not be silently dropped from the index.
    markdown = "This overview text has no heading.\n\n# Q1: A question?\n\nAn answer."
    chunks = chunk_markdown(markdown)
    joined = "\n".join(c.content for c in chunks)
    assert "This overview text has no heading." in joined
    assert any(c.heading_path == ["Overview"] for c in chunks)
    assert any(c.heading_path == ["Q1: A question?"] for c in chunks)


def test_chunk_markdown_splits_by_headers():
    markdown = """# Policy

Top intro.

## Returns

Return within 30 days.

## Warranty

One year warranty.
"""
    chunks = chunk_markdown(markdown)
    assert len(chunks) >= 2
    assert any("Returns" in chunk.content for chunk in chunks)
    assert any("Warranty" in chunk.content for chunk in chunks)


def test_chunk_markdown_splits_long_sections():
    body = "word " * 800
    markdown = f"## Long section\n\n{body}"
    chunks = chunk_markdown(markdown, max_chars=500, overlap=50)
    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_chunk_markdown_skips_empty_wrapper_headings():
    markdown = """# Introduction

Intro body.

# Q&A

## Q1: First question?

Answer one.

## Q2: Second question?

Answer two.

# Tone

Tone body.
"""
    chunks = chunk_markdown(markdown)
    titles = [" > ".join(chunk.heading_path) for chunk in chunks]
    assert "Q&A" not in titles
    assert any("Q1: First question?" in title for title in titles)
    assert any("Q2: Second question?" in title for title in titles)
    assert len(chunks) == 4
