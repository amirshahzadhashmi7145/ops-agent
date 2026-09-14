from app.services.tool_log import clip_json, redact_headers


def test_redact_headers_masks_secrets():
    redacted = redact_headers(
        {
            "Authorization": "Bearer secret-token",
            "X-Api-Key": "abc123",
            "Cookie": "session=1",
            "Content-Type": "application/json",
        }
    )
    assert redacted["Authorization"] == "***"
    assert redacted["X-Api-Key"] == "***"
    assert redacted["Cookie"] == "***"
    assert redacted["Content-Type"] == "application/json"


def test_clip_json_keeps_small_payloads():
    payload = {"ok": True, "count": 2}
    assert clip_json(payload) == payload


def test_clip_json_truncates_large_payloads():
    clipped = clip_json({"body": "x" * 50}, max_chars=20)
    assert clipped["_truncated"] is True
    assert "preview" in clipped
