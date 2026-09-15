from app.data.nexar_playbook import AGENT_RULES, CATEGORIES, KB_ARTICLES, SOP_DOCUMENTS
from app.services.kb_chunker import chunk_markdown
from app.services.sop_device_routing import DOC_CLASSIC, DOC_CONNECT, DOC_HARDWARE
from app.services.sop_ingestion import _build_chunk_content


def test_playbook_covers_device_routing_sops():
    titles = {document["title"] for document in SOP_DOCUMENTS}
    assert DOC_CLASSIC in titles
    assert DOC_CONNECT in titles
    assert DOC_HARDWARE in titles

    processes = [process["title"] for document in SOP_DOCUMENTS for process in document["processes"]]
    assert "Nexar Classic App Connectivity" in processes
    assert "Sim Triage" in processes
    assert "Hardware Malfunction" in processes
    assert "Look up customer devices" in processes


def test_kb_articles_chunk_into_headed_sections():
    assert len(KB_ARTICLES) >= 8
    for article in KB_ARTICLES:
        chunks = chunk_markdown(article["markdown"])
        assert chunks, article["title"]
        assert any(chunk.heading_path for chunk in chunks)


def test_sop_process_chunk_content_includes_tools():
    process = SOP_DOCUMENTS[0]["processes"][0]
    content = _build_chunk_content(process)
    assert process["title"] in content
    assert process["tools"][0] in content


def test_categories_and_rules_are_populated():
    slugs = {item["slug"] for item in CATEGORIES}
    assert {"subscription", "returns", "connectivity", "hardware", "classic-connectivity"} <= slugs
    categories = {item["category"] for item in AGENT_RULES}
    assert categories == {
        "business_context",
        "escalations",
        "response_tone_style",
        "agent_capabilities",
    }
