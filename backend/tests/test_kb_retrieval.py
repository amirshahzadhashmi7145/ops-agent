from uuid import uuid4

from app.services.kb_retrieval import KbSearchResult, _cap_payload, _select_diverse_sections


def _hit(ref_id, section, score):
    return KbSearchResult(
        reference_id=ref_id,
        title=str(ref_id),
        heading_path=[section],
        content=f"{ref_id}:{section}",
        score=score,
    )


def test_diverse_sections_dedupes_same_section():
    ref = uuid4()
    # Two candidate chunks from the same section -> one result.
    candidates = [_hit(ref, "Intro", 0.9), _hit(ref, "Intro", 0.8)]
    result = _select_diverse_sections(candidates, limit=8, max_per_reference=3)
    assert len(result) == 1


def test_diverse_sections_caps_dominant_article():
    a, b = uuid4(), uuid4()
    # Article A scores higher across 5 sections; B has one lower-scoring section.
    candidates = [
        _hit(a, "A1", 0.95),
        _hit(a, "A2", 0.94),
        _hit(a, "A3", 0.93),
        _hit(a, "A4", 0.92),
        _hit(a, "A5", 0.91),
        _hit(b, "B1", 0.70),
    ]
    result = _select_diverse_sections(candidates, limit=4, max_per_reference=3)
    refs = [hit.reference_id for hit in result]
    # A is capped at 3 in the first pass; B must be surfaced before A's 4th/5th.
    assert refs.count(a) == 3
    assert b in refs


def test_diverse_sections_backfills_single_article():
    # When only one article is relevant, the cap must not starve the results.
    a = uuid4()
    candidates = [_hit(a, f"S{i}", 0.9 - i * 0.01) for i in range(6)]
    result = _select_diverse_sections(candidates, limit=5, max_per_reference=3)
    assert len(result) == 5
    assert all(hit.reference_id == a for hit in result)


def test_cap_payload_limits_total_chars():
    results = [
        {"reference_id": "1", "title": "A", "heading_path": [], "content": "a" * 5000, "score": 0.9},
        {"reference_id": "2", "title": "B", "heading_path": [], "content": "b" * 5000, "score": 0.8},
    ]
    capped = _cap_payload(results)
    total = sum(len(item["content"]) for item in capped)
    assert total <= 12000
    assert len(capped) >= 1


def test_cap_payload_truncates_oversized_entry():
    results = [
        {"reference_id": "1", "title": "A", "heading_path": [], "content": "x" * 20000, "score": 0.9},
    ]
    capped = _cap_payload(results)
    assert len(capped) == 1
    assert capped[0]["content"].endswith("…")
