"""Catalog integrity for app/data/internal_tools.json."""

from collections import Counter

from app.services.internal_tools_seed import ALIAS_NAMES, load_internal_tool_defs

# Stable catalog size: 38 canonical tools + 5 generic aliases.
EXPECTED_TOOL_COUNT = 43


def test_internal_tools_catalog_shape_and_aliases():
    tools = load_internal_tool_defs()
    assert len(tools) == EXPECTED_TOOL_COUNT

    names = [item["name"] for item in tools]
    assert len(names) == len(set(names)), "tool names must be unique"

    for item in tools:
        assert item.get("name") and isinstance(item["name"], str)
        assert item.get("http_method") and isinstance(item["http_method"], str)
        assert item.get("url") and isinstance(item["url"], str)
        assert item.get("description") and isinstance(item["description"], str)
        # Accept either "method" legacy key absence — catalog uses http_method.
        assert "method" not in item or item["method"] == item["http_method"]

    alias_names = {n for n in names if n in ALIAS_NAMES}
    assert alias_names == ALIAS_NAMES

    # Non-alias tools must not collide on method+url (aliases intentionally share endpoints).
    pairs = [
        (item["http_method"].upper(), item["url"])
        for item in tools
        if item["name"] not in ALIAS_NAMES
    ]
    counts = Counter(pairs)
    duplicates = [pair for pair, count in counts.items() if count > 1]
    assert duplicates == [], f"duplicate method+url among canonical tools: {duplicates}"
