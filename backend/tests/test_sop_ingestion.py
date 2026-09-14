from app.services.llm_json import parse_json_object
from app.services.sop_ingestion import _normalize_tools


def test_parse_plain_json_object():
    assert parse_json_object('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_parse_fenced_json():
    raw = '```json\n{"summary": "s", "processes": []}\n```'
    assert parse_json_object(raw) == {"summary": "s", "processes": []}


def test_parse_json_with_prose_around_it():
    raw = 'Here is the JSON you asked for:\n{"processes": [{"title": "T"}]}\nHope that helps!'
    parsed = parse_json_object(raw)
    assert parsed is not None
    assert parsed["processes"][0]["title"] == "T"


def test_parse_json_with_raw_newlines_in_string():
    # LLMs often emit literal newlines inside string values; must still parse.
    raw = '{"summary": "line one\nline two", "processes": []}'
    parsed = parse_json_object(raw)
    assert parsed is not None
    assert "line one" in parsed["summary"]


def test_parse_unparseable_returns_none():
    assert parse_json_object("not json at all") is None
    assert parse_json_object("") is None


def test_normalize_tools_keeps_all_process_tools():
    # Union of tools list + step tools; nothing dropped by intersecting with mentions.
    process = {
        "tools": ["lookup_customer_by_email"],
        "steps": [{"type": "call_tool", "tool": "cancel_subscription"}],
    }
    result = _normalize_tools(process, mentioned={"lookup_customer_by_email"})
    assert result == ["cancel_subscription", "lookup_customer_by_email"]


def test_normalize_tools_falls_back_to_mentions_when_process_has_none():
    process = {"tools": [], "steps": [{"type": "inform", "instruction": "hi"}]}
    result = _normalize_tools(process, mentioned={"initiate_return"})
    assert result == ["initiate_return"]


def test_normalize_tools_normalizes_names_and_updates_steps():
    process = {"tools": ["@Cancel-Subscription"], "steps": [{"tool": "@Cancel-Subscription"}]}
    result = _normalize_tools(process, mentioned=set())
    assert result == ["cancel_subscription"]
    assert process["steps"][0]["tool"] == "cancel_subscription"
