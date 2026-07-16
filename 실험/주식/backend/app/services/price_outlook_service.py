from __future__ import annotations

import math
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyPrice, DailyReport


def build_price_outlook(db: Session, report: DailyReport) -> dict:
    rows = db.scalars(
        select(DailyPrice)
        .where(DailyPrice.stock_id == report.stock_id)
        .order_by(DailyPrice.date.desc())
        .limit(180)
    ).all()
    return calculate_price_outlook(report, list(reversed(rows)))


def calculate_price_outlook(report: DailyReport, rows: Sequence[DailyPrice]) -> dict:
    current = _number(report.current_price)
    valid_rows = [row for row in rows if _number(row.close_price) is not None]
    if current is None and valid_rows:
        current = _number(valid_rows[-1].close_price)
    if current is None or current <= 0:
        return {
            "day1_expected_price": None,
            "day1_expected_return": None,
            "day2_expected_price": None,
            "day2_expected_return": None,
            "sell_target_price": None,
            "sell_target_return": None,
            "sell_target_low": None,
            "sell_target_high": None,
            "support_price": None,
            "resistance_price": None,
            "trailing_stop_percent": None,
            "sell_strategy": "가격 데이터가 부족해 매도 목표를 계산하지 못했습니다.",
            "sell_target_basis": [],
        }

    probability = max(0.0, min(1.0, report.up_probability / 100))
    low = float(report.expected_range_low)
    high = float(report.expected_range_high)
    confidence_factor = {"high": 0.9, "medium": 0.75, "low": 0.55}.get(
        report.confidence_level, 0.55
    )
    weighted_return = (low * (1 - probability) + high * probability) * confidence_factor
    day1_return = round(weighted_return, 2)
    day2_return = round(weighted_return * math.sqrt(2), 2)
    day1_price = _price_from_return(current, day1_return)
    day2_price = _price_from_return(current, day2_return)

    latest = valid_rows[-1] if valid_rows else None
    atr = _number(latest.atr) if latest else None
    atr_percent = (atr / current * 100) if atr and atr > 0 else _fallback_atr_percent(valid_rows)
    atr_percent = max(0.6, min(15.0, atr_percent))

    resistance_price = _nearest_resistance(valid_rows, current)
    support_price = _nearest_support(valid_rows, current)
    resistance_return = (
        (resistance_price / current - 1) * 100 if resistance_price is not None else None
    )
    volatility_target = atr_percent * (1.15 + max(0.0, probability - 0.5) * 1.8)
    model_target = max(0.8, day2_return)
    target_return = max(model_target, volatility_target)

    if resistance_return is not None and resistance_return > 0.8:
        if resistance_return <= target_return * 1.35:
            target_return = max(
                0.8,
                resistance_return - max(0.25, min(1.5, atr_percent * 0.15)),
            )
        else:
            target_return = min(target_return, resistance_return)

    rsi = _number(latest.rsi) if latest else None
    if rsi is not None and rsi >= 70:
        target_return = min(target_return, max(1.0, atr_percent * 1.25, model_target * 0.9))
    if report.up_probability < 50:
        target_return = min(target_return, max(0.8, atr_percent * 1.1))
    target_return = round(max(0.8, min(25.0, target_return)), 2)

    zone_half_width = max(0.4, min(2.0, atr_percent * 0.2))
    target_low_return = max(0.5, target_return - zone_half_width)
    target_high_return = target_return + zone_half_width
    trailing_stop = round(max(1.5, min(8.0, atr_percent * 0.75)), 1)

    ma20 = _number(latest.ma20) if latest else None
    ma60 = _number(latest.ma60) if latest else None
    basis = [
        _trend_description(current, ma20, ma60),
        f"14일 ATR 기준 일일 변동폭 약 {atr_percent:.1f}%",
    ]
    if rsi is not None:
        if rsi >= 70:
            basis.append(f"RSI {rsi:.1f}로 과열 구간에 가까워 목표가 도달 시 이익 확정 우선")
        elif rsi >= 55:
            basis.append(f"RSI {rsi:.1f}로 상승 모멘텀이 우세")
        elif rsi <= 35:
            basis.append(f"RSI {rsi:.1f}로 약세·과매도 구간")
        else:
            basis.append(f"RSI {rsi:.1f}로 중립 구간")
    if resistance_price is not None:
        basis.append(f"최근 120거래일의 가까운 저항 가격 {resistance_price:,.2f} 반영")
    else:
        basis.append("뚜렷한 상단 저항이 없어 변동성과 예측값 중심으로 산출")

    return {
        "day1_expected_price": day1_price,
        "day1_expected_return": day1_return,
        "day2_expected_price": day2_price,
        "day2_expected_return": day2_return,
        "sell_target_price": _price_from_return(current, target_return),
        "sell_target_return": target_return,
        "sell_target_low": _price_from_return(current, target_low_return),
        "sell_target_high": _price_from_return(current, target_high_return),
        "support_price": support_price,
        "resistance_price": resistance_price,
        "trailing_stop_percent": trailing_stop,
        "sell_strategy": (
            "목표 구간에서 보유 수량의 50~70%를 분할매도하고, "
            f"잔여 수량은 목표가 대비 {trailing_stop:.1f}% 하락하거나 "
            "5일 이동평균을 종가로 이탈할 때 추가 정리를 검토하세요."
        ),
        "sell_target_basis": basis,
    }


def _nearest_resistance(rows: Sequence[DailyPrice], current: float) -> float | None:
    recent = list(rows[-120:])
    candidates: list[float] = []
    for index, row in enumerate(recent):
        high = _number(row.high_price)
        if high is None or high <= current * 1.008:
            continue
        left = recent[max(0, index - 3) : index]
        right = recent[index + 1 : index + 4]
        neighboring_highs = [
            value
            for neighbor in [*left, *right]
            if (value := _number(neighbor.high_price)) is not None
        ]
        if not neighboring_highs or high >= max(neighboring_highs):
            candidates.append(high)
    return min(candidates) if candidates else None


def _nearest_support(rows: Sequence[DailyPrice], current: float) -> float | None:
    recent = list(rows[-120:])
    candidates: list[float] = []
    for index, row in enumerate(recent):
        low = _number(getattr(row, "low_price", None) or row.close_price)
        if low is None or low >= current * 0.995:
            continue
        left = recent[max(0, index - 3) : index]
        right = recent[index + 1 : index + 4]
        neighboring_lows = [
            value
            for neighbor in [*left, *right]
            if (
                value := _number(
                    getattr(neighbor, "low_price", None) or neighbor.close_price
                )
            )
            is not None
        ]
        if not neighboring_lows or low <= min(neighboring_lows):
            candidates.append(low)
    return max(candidates) if candidates else None


def _fallback_atr_percent(rows: Sequence[DailyPrice]) -> float:
    changes = [
        abs(float(row.change_rate))
        for row in rows[-20:]
        if _number(row.change_rate) is not None
    ]
    return sum(changes) / len(changes) if changes else 2.0


def _trend_description(current: float, ma20: float | None, ma60: float | None) -> str:
    if ma20 is not None and ma60 is not None and current > ma20 > ma60:
        return "현재가가 20일·60일 이동평균 위에 있는 정배열 상승 추세"
    if ma20 is not None and current > ma20:
        return "현재가가 20일 이동평균 위에 있는 단기 상승 추세"
    if ma20 is not None and ma60 is not None and current < ma20 < ma60:
        return "현재가가 20일·60일 이동평균 아래인 약세 추세"
    return "이동평균선 배열이 혼조인 구간"


def _price_from_return(current: float, return_percent: float) -> float:
    return round(current * (1 + return_percent / 100), 2)


def _number(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None
