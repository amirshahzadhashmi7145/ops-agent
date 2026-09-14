from app.models.resource import Resource
from app.services.agent_runtime import build_resource_payload, missing_required_params


class FakeResource:
    name = "getDeviceHealth"
    parameters = [
        {
            "name": "serial",
            "type": "string",
            "required": True,
            "description": "serial",
            "default_value": "N1-SAVED",
        }
    ]


def test_build_resource_payload_uses_default_value():
    payload = build_resource_payload(FakeResource(), {})  # type: ignore[arg-type]
    assert payload["serial"] == "N1-SAVED"


def test_build_resource_payload_prefers_llm_argument():
    payload = build_resource_payload(FakeResource(), {"serial": "N1-OVERRIDE"})  # type: ignore[arg-type]
    assert payload["serial"] == "N1-OVERRIDE"


def test_missing_required_params_detects_empty():
    payload = build_resource_payload(
        type(
            "R",
            (),
            {
                "parameters": [
                    {
                        "name": "serial",
                        "type": "string",
                        "required": True,
                        "default_value": "",
                    }
                ]
            },
        )(),
        {},
    )
    missing = missing_required_params(
        type("R", (), {"parameters": FakeResource.parameters})(),  # type: ignore[arg-type]
        payload,
    )
    assert missing == ["serial"]
