"""SOP @mention / bare-tool name normalization."""

from app.services.sop_ingestion import (
    _normalize_tool_name,
    _normalize_tools,
    extract_mentions,
)


def test_extract_mentions_from_at_and_bare_forms():
    text = """
    1. Call @lookup_customer_by_email with the address.
    2. Then use list_customer_devices for inventory.
    3. Optionally invoke @Cancel-Subscription after confirm.
    4. Email system@ops.internal is not a tool.
    """
    mentions = extract_mentions(text)
    assert "lookup_customer_by_email" in mentions
    assert "list_customer_devices" in mentions
    assert "Cancel-Subscription" in mentions
    assert "ops" in mentions  # from @ops.internal email — normalize layer filters later


def test_normalize_tool_name_strips_at_and_snake_cases():
    assert _normalize_tool_name("@Lookup_Account") == "lookup_account"
    assert _normalize_tool_name("Cancel-Subscription") == "cancel_subscription"
    assert _normalize_tool_name("  getDeviceHealth ") == "getdevicehealth"
    assert _normalize_tool_name("@list_customer_assets") == "list_customer_assets"


def test_normalize_tools_accepts_at_tool_vs_snake():
    process = {
        "tools": ["@Lookup-Account", "get_order_status"],
        "steps": [
            {"type": "call_tool", "tool": "@List_Customer_Assets"},
            {"type": "inform", "instruction": "done"},
        ],
    }
    result = _normalize_tools(process, mentioned={"lookup_account"})
    assert result == ["get_order_status", "list_customer_assets", "lookup_account"]
    assert process["steps"][0]["tool"] == "list_customer_assets"
