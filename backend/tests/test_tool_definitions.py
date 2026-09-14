"""Tests for tool definitions and agent helpers."""

import pytest

from app.schemas.resource import ParameterSchema
from app.services.tool_definitions import is_greeting_message, resource_to_tool_definition


class FakeResource:
    def __init__(self) -> None:
        self.name = "getDeviceHealth"
        self.description = "Get device health by serial number"
        self.parameters = [
            {
                "name": "serial",
                "type": "string",
                "required": True,
                "description": "Device serial number",
                "default_value": "",
            }
        ]


def test_is_greeting_message():
    assert is_greeting_message("hi")
    assert is_greeting_message("Hello!")
    assert not is_greeting_message("get my device health")


def test_resource_to_tool_definition():
    tool = resource_to_tool_definition(FakeResource())  # type: ignore[arg-type]
    assert tool["function"]["name"] == "getDeviceHealth"
    assert "serial" in tool["function"]["parameters"]["properties"]
    assert tool["function"]["parameters"]["required"] == ["serial"]


def test_parameter_schema_default_value():
    param = ParameterSchema(name="serial", type="string", default_value="N1-123")
    assert param.default_value == "N1-123"
