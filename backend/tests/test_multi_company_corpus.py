"""Multi-company corpus packs under app/data/companies/."""

from app.data.support_playbook import SOP_DOCUMENTS
from app.services.company_corpus import list_company_ids, load_all_companies, load_company
from app.services.internal_tools_seed import ALIAS_NAMES, load_internal_tool_defs
from app.services.sop_ingestion import extract_mentions

REQUIRED_COMPANY_KEYS = {"id", "brand", "articles"}
REQUIRED_ARTICLE_KEYS = {"title", "markdown"}


def _known_tool_names() -> set[str]:
    return {item["name"] for item in load_internal_tool_defs()} | set(ALIAS_NAMES)


def test_company_packs_have_required_fields():
    ids = list_company_ids()
    assert len(ids) >= 6
    companies = load_all_companies()
    assert len(companies) == len(ids)

    for company in companies:
        missing = REQUIRED_COMPANY_KEYS - set(company)
        assert not missing, f"{company.get('id')}: missing {missing}"
        assert company["id"] and isinstance(company["id"], str)
        assert company["brand"].strip(), "company name (brand) must be non-empty"
        assert company["articles"], f"{company['id']}: articles (KB) must be non-empty"

        # company_corpus.apply_company_articles uses title/markdown; optional summary ok.
        for article in company["articles"]:
            for key in REQUIRED_ARTICLE_KEYS:
                assert str(article.get(key) or "").strip(), f"{company['id']}: empty {key}"

        # Optional SOPs / rules when present (not used by company_corpus today).
        for key in ("sops", "workflows", "rules"):
            if key not in company:
                continue
            assert isinstance(company[key], list)
            for item in company[key]:
                assert item, f"{company['id']}: empty {key} entry"


def test_company_ids_match_filenames():
    for company_id in list_company_ids():
        pack = load_company(company_id)
        assert pack["id"] == company_id


def test_sop_tool_mentions_resolve_to_known_tools():
    """Playbook SOP tools (+ any @mentions in company packs) must be catalogued."""
    known = _known_tool_names()
    unknown: list[str] = []

    for document in SOP_DOCUMENTS:
        for process in document.get("processes") or []:
            for tool in process.get("tools") or []:
                if tool not in known:
                    unknown.append(tool)
            for step in process.get("steps") or []:
                tool = step.get("tool")
                if tool and tool not in known:
                    unknown.append(tool)
        # Structured @mentions in SOP body (ignore email fragments like @ops.internal).
        for mention in extract_mentions(document.get("raw_text") or ""):
            if "_" in mention or mention in known:
                if mention not in known:
                    unknown.append(mention)

    for company in load_all_companies():
        for article in company["articles"]:
            blob = "\n".join(
                [
                    str(article.get("title") or ""),
                    str(article.get("summary") or ""),
                    str(article.get("markdown") or ""),
                ]
            )
            for mention in extract_mentions(blob):
                if "_" in mention or mention in known:
                    if mention not in known:
                        unknown.append(mention)
        for sop in company.get("sops") or company.get("workflows") or []:
            text = sop if isinstance(sop, str) else str(sop.get("raw_text") or sop.get("content") or "")
            for mention in extract_mentions(text):
                if mention not in known:
                    unknown.append(mention)
            for tool in (sop.get("tools") if isinstance(sop, dict) else None) or []:
                if tool not in known:
                    unknown.append(tool)

    assert unknown == [], f"unknown tool mentions: {sorted(set(unknown))}"
