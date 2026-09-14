from app.services.sop_device_routing import is_confident_match


def _m(pid: str, score: float) -> dict:
    return {"process_id": pid, "score": score}


def test_none_best_is_not_confident():
    assert is_confident_match(None, [], threshold=0.5, margin=0.08) is False


def test_below_threshold_is_not_confident():
    best = _m("a", 0.4)
    assert is_confident_match(best, [best], threshold=0.5, margin=0.08) is False


def test_clear_winner_is_confident():
    best, second = _m("a", 0.70), _m("b", 0.50)
    assert is_confident_match(best, [best, second], threshold=0.5, margin=0.08) is True


def test_near_tie_is_not_confident():
    # Both clear the threshold, but the gap (0.03) is under the 0.08 margin -> ambiguous.
    best, second = _m("a", 0.55), _m("b", 0.52)
    assert is_confident_match(best, [best, second], threshold=0.5, margin=0.08) is False


def test_single_match_above_threshold_is_confident():
    best = _m("a", 0.60)
    assert is_confident_match(best, [best], threshold=0.5, margin=0.08) is True
