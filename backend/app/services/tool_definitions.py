import re
from typing import Any

from app.models.resource import Resource

TYPE_MAP = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
}


def resource_to_tool_definition(resource: Resource) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in resource.parameters or []:
        if not isinstance(param, dict):
            continue
        name = str(param.get("name", "")).strip()
        if not name:
            continue
        param_type = TYPE_MAP.get(str(param.get("type", "string")), "string")
        properties[name] = {
            "type": param_type,
            "description": str(param.get("description") or f"{name} parameter"),
        }
        if param.get("required"):
            required.append(name)

    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        parameters_schema["required"] = required

    return {
        "type": "function",
        "function": {
            "name": resource.name,
            "description": resource.description or f"Call the {resource.name} API.",
            "parameters": parameters_schema,
        },
    }


SEARCH_KNOWLEDGE_BASE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Search the internal knowledge base for policies, FAQs, and product documentation. "
            "Use when the user asks about company policies, procedures, or product details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query describing what information is needed.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

SEARCH_SOP_PROCESSES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_sop_processes",
        "description": (
            "Search executable SOP processes for multi-step operational workflows "
            "(cancel subscription, return device, etc.). Use when the user wants to "
            "complete an action that must follow a defined procedure."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of the task the user wants done.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def resources_to_tool_definitions(resources: list[Resource]) -> list[dict[str, Any]]:
    return [resource_to_tool_definition(resource) for resource in resources]


def knowledge_base_tool_definition() -> dict[str, Any]:
    return SEARCH_KNOWLEDGE_BASE_TOOL


def sop_processes_tool_definition() -> dict[str, Any]:
    return SEARCH_SOP_PROCESSES_TOOL


def build_tool_definitions(
    resources: list[Resource],
    *,
    allowed_tool_names: set[str] | None = None,
    enable_kb_search: bool = True,
    enable_sop_matching: bool = True,
) -> list[dict[str, Any]]:
    resource_tools = resources_to_tool_definitions(resources)
    if allowed_tool_names is not None:
        resource_tools = [
            tool
            for tool in resource_tools
            if tool.get("function", {}).get("name") in allowed_tool_names
        ]
    built: list[dict[str, Any]] = []
    if enable_kb_search:
        built.append(knowledge_base_tool_definition())
    if enable_sop_matching:
        built.append(sop_processes_tool_definition())
    built.extend(resource_tools)
    return built


GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|yo|good\s+(morning|afternoon|evening)|howdy|sup|what'?s\s+up)[!.?\s]*$",
    re.IGNORECASE,
)


def is_greeting_message(message: str) -> bool:
    return bool(GREETING_PATTERN.match(message.strip()))
