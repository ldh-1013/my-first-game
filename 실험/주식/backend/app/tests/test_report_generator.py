from app.services.report_generator import build_report_content


def test_report_contains_required_sections():
    content = build_report_content(
        stock_name="Example",
        latest={
            "close": 120,
            "ma20": 115,
            "rsi": 58,
            "recent_5d_return": 2.4,
        },
        sentiment_results=[],
        risk_score=30,
        prediction={
            "up_probability": 57,
            "confidence_level": "medium",
        },
    )
    required = {
        "positive_factors",
        "negative_factors",
        "neutral_factors",
        "news_summary",
        "technical_analysis",
        "flow_analysis",
        "key_risks",
        "user_checklist",
        "final_view",
    }
    assert required.issubset(content)


def test_report_avoids_prohibited_guarantee_language():
    content = build_report_content(
        stock_name="Example",
        latest=None,
        sentiment_results=[],
        risk_score=80,
        prediction={"up_probability": 50, "confidence_level": "low"},
    )
    combined = " ".join(str(value) for value in content.values())
    prohibited = ["수익 보장", "무조건 오른다", "반드시 매도", "매수 추천"]
    assert not any(term in combined for term in prohibited)

