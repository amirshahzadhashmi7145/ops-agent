from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.api.chat import LIVE_IDLE, _apply_idle_end, _mark_ended, _mark_live, _preview_text
from app.models.conversation import ConversationStatus


def test_preview_text_trims_and_ellipsizes():
    assert _preview_text(None) is None
    assert _preview_text("   ") is None
    assert _preview_text("hello world") == "hello world"
    long = "x" * 200
    preview = _preview_text(long, limit=20)
    assert preview is not None
    assert preview.endswith("…")
    assert len(preview) == 21


def test_mark_live_and_ended():
    conv = SimpleNamespace(status=ConversationStatus.ended, ended_at=datetime.now(timezone.utc))
    _mark_live(conv)
    assert conv.status == ConversationStatus.live
    assert conv.ended_at is None

    _mark_ended(conv, when=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert conv.status == ConversationStatus.ended
    assert conv.ended_at == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_apply_idle_end_only_for_stale_live():
    now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
    fresh = SimpleNamespace(
        status=ConversationStatus.live,
        updated_at=now - timedelta(minutes=10),
        ended_at=None,
    )
    assert _apply_idle_end(fresh, now) is False
    assert fresh.status == ConversationStatus.live

    stale = SimpleNamespace(
        status=ConversationStatus.live,
        updated_at=now - LIVE_IDLE - timedelta(minutes=5),
        ended_at=None,
    )
    assert _apply_idle_end(stale, now) is True
    assert stale.status == ConversationStatus.ended
    assert stale.ended_at is not None

    already = SimpleNamespace(
        status=ConversationStatus.ended,
        updated_at=now - LIVE_IDLE * 2,
        ended_at=now - LIVE_IDLE,
    )
    assert _apply_idle_end(already, now) is False
