from app.services.tool_definitions import build_tool_definitions, knowledge_base_tool_definition


def test_knowledge_base_tool_definition_shape():
    tool = knowledge_base_tool_definition()
    assert tool["function"]["name"] == "search_knowledge_base"
    assert "query" in tool["function"]["parameters"]["properties"]


def test_build_tool_definitions_includes_kb_tool():
    tools = build_tool_definitions([])
    assert tools[0]["function"]["name"] == "search_knowledge_base"
