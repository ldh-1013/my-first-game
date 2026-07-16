def build_report_content(
    *,
    stock_name: str,
    latest: dict | None,
    sentiment_results: list[dict],
    risk_score: float,
    prediction: dict,
) -> dict:
    positive: list[str] = []
    negative: list[str] = []
    neutral: list[str] = []
    for result in sentiment_results:
        title = result.get("title") or result.get("original_title") or "제목 없는 뉴스"
        target = {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
        }.get(result.get("sentiment_label"), neutral)
        if title not in target:
            target.append(title)

    if latest:
        technical = (
            f"현재가 {_format_number(latest.get('close'), 2)} · "
            f"20일 이동평균 {_format_number(latest.get('ma20'), 2)} · "
            f"RSI {_format_number(latest.get('rsi'), 1)}"
        )
        five_day = latest.get("recent_5d_return")
        flow = (
            f"최근 5거래일 변동률 {_format_number(five_day, 2)}%"
            if five_day is not None
            else "최근 5거래일 흐름을 계산할 데이터가 부족합니다."
        )
    else:
        technical = "가격 데이터가 없어 기술 지표를 계산하지 못했습니다."
        flow = "거래 흐름 데이터가 부족합니다."

    if risk_score >= 65:
        final_view = "주의 필요"
    elif prediction["confidence_level"] == "low":
        final_view = "추가 확인 필요"
    elif prediction["up_probability"] >= 60:
        final_view = "상승 우위 관찰"
    else:
        final_view = "보유 또는 관찰"

    risks = []
    if risk_score >= 50:
        risks.append("변동성 또는 데이터 부족 위험이 큽니다.")
    if prediction["confidence_level"] == "low":
        risks.append("예측 신뢰도가 낮아 추가 확인이 필요합니다.")
    if not risks:
        risks.append("시장 급변과 무료 데이터 지연 가능성을 확인하세요.")

    positive_count = sum(row.get("sentiment_label") == "positive" for row in sentiment_results)
    negative_count = sum(row.get("sentiment_label") == "negative" for row in sentiment_results)
    neutral_count = len(sentiment_results) - positive_count - negative_count
    if not sentiment_results:
        news_summary = f"{stock_name} 관련 최신 기사를 수집하지 못했습니다."
        neutral.append("수집된 최신 뉴스가 없어 뉴스 영향 판단이 제한적입니다.")
    elif positive_count > negative_count and positive_count > neutral_count:
        news_summary = f"관련 기사 {len(sentiment_results)}건 중 긍정 뉴스가 우세합니다."
    elif negative_count > positive_count and negative_count > neutral_count:
        news_summary = f"관련 기사 {len(sentiment_results)}건 중 부정 뉴스가 우세합니다."
    else:
        news_summary = f"관련 기사 {len(sentiment_results)}건의 뉴스 흐름은 중립·혼조입니다."

    return {
        "positive_factors": positive[:5],
        "negative_factors": negative[:5],
        "neutral_factors": neutral[:5],
        "news_summary": news_summary,
        "technical_analysis": technical,
        "flow_analysis": flow,
        "key_risks": " ".join(risks),
        "user_checklist": "뉴스 원문, 공시, 최근 실적, 본인의 손실 감내 범위를 확인하세요.",
        "final_view": final_view,
    }


def _format_number(value: float | None, digits: int) -> str:
    return f"{value:.{digits}f}" if value is not None else "데이터 없음"
