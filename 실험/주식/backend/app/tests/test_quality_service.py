from app.services.quality_service import data_quality_score, decision_status, surge_status
from app.services.recommendation_engine import select_candidates


class Report:
    up_probability = 78
    expected_range_high = 8


def test_surge_is_flagged_but_not_excluded_from_top5():
    warning, reason = surge_status(
        {"change_rate": 14, "recent_5d_return": 24, "volume_change_rate": 180}
    )
    candidate = {
        "confidence_level": "medium",
        "report": Report(),
        "final_score": 80,
        "surge_warning": warning,
    }
    assert warning is True
    assert "일간 상승률" in reason
    assert select_candidates([candidate]) == [candidate]


def test_low_quality_forces_decision_defer():
    quality = data_quality_score(
        price_rows=5,
        latest_price=100,
        news_count=0,
        has_financials=False,
    )
    assert quality < 50
    assert decision_status(quality, "low", 75, 80) == "defer"
