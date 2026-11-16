"""Resource list ordering and alias-tool identification."""

from app.api.resources import resource_name_sort_key, sorted_resource_names
from app.services.internal_tools_seed import ALIAS_NAMES, is_alias_tool, load_internal_tool_defs


def test_sorted_resource_names_matches_name_asc_for_mixed_case():
    # Documents expected behavior of order_by(Resource.name.asc()) for ASCII names:
    # plain string order (uppercase before lowercase in default C/ASCII collation).
    names = ["zeta", "Alpha", "beta", "alpha", "Zulu"]
    assert sorted_resource_names(names) == sorted(names)
    assert sorted_resource_names(names) == ["Alpha", "Zulu", "alpha", "beta", "zeta"]
    assert resource_name_sort_key("Beta") == "Beta"
    assert resource_name_sort_key("") == ""


def test_alias_tools_are_identifiable():
    expected = {
        "lookup_account",
        "list_customer_assets",
        "lookup_asset",
        "get_asset_health",
        "get_order_status",
    }
    assert ALIAS_NAMES == expected
    for name in expected:
        assert is_alias_tool(name)
    assert not is_alias_tool("lookup_customer_by_email")
    assert not is_alias_tool("getDeviceHealth")

    seeded = {item["name"] for item in load_internal_tool_defs()}
    assert expected <= seeded
