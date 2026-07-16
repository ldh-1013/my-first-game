from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailyPrice, DailyReport, Stock
from app.services.price_outlook_service import build_price_outlook


RISK_SETTINGS = {
    "low": {
        "invest_ratio": 0.70,
        "max_weight": 0.18,
        "positions": 6,
        "min_quality": 72,
        "min_probability": 60,
        "correlation_penalty": 0.65,
        "volatility_power": 1.2,
    },
    "medium": {
        "invest_ratio": 0.85,
        "max_weight": 0.22,
        "positions": 7,
        "min_quality": 62,
        "min_probability": 55,
        "correlation_penalty": 0.45,
        "volatility_power": 0.8,
    },
    "high": {
        "invest_ratio": 0.95,
        "max_weight": 0.28,
        "positions": 8,
        "min_quality": 52,
        "min_probability": 51,
        "correlation_penalty": 0.25,
        "volatility_power": 0.45,
    },
}


def build_allocation_plan(
    db: Session,
    *,
    capital: float,
    currency: str,
    risk_profile: str,
    max_positions: int | None = None,
) -> dict:
    report_date = db.scalar(select(func.max(DailyReport.report_date)))
    if report_date is None:
        return _empty_plan(capital, currency, risk_profile, "분석 리포트가 없습니다.")

    reports = db.scalars(
        select(DailyReport)
        .join(Stock, Stock.id == DailyReport.stock_id)
        .where(
            DailyReport.report_date == report_date,
            Stock.currency == currency,
            Stock.is_listed.is_(True),
            DailyReport.current_price.is_not(None),
        )
        .order_by(DailyReport.final_score.desc())
    ).all()

    candidates = []
    for report in reports:
        stock = db.get(Stock, report.stock_id)
        if not stock or not report.current_price or report.current_price <= 0:
            continue
        latest = db.scalar(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == report.stock_id,
                DailyPrice.close_price.is_not(None),
            )
            .order_by(DailyPrice.date.desc())
        )
        outlook = build_price_outlook(db, report)
        expected_return = float(outlook.get("day2_expected_return") or 0)
        annual_volatility = float(
            latest.volatility_20d
            if latest and latest.volatility_20d is not None
            else 45
        )
        returns = _return_series(db, report.stock_id)
        candidates.append(
            {
                "ticker": stock.ticker,
                "name": stock.name,
                "market": stock.market,
                "currency": stock.currency,
                "current_price": float(report.current_price),
                "up_probability": float(report.up_probability),
                "expected_2d_return": expected_return,
                "downside_scenario_return": round(
                    float(report.expected_range_low) * math.sqrt(2), 2
                ),
                "data_quality_score": float(report.data_quality_score),
                "final_score": float(report.final_score),
                "annual_volatility": max(5.0, annual_volatility),
                "confidence_level": report.confidence_level,
                "surge_warning": bool(report.surge_warning),
                "rsi": float(latest.rsi) if latest and latest.rsi is not None else None,
                "returns": returns,
            }
        )

    return optimize_allocation(
        candidates,
        capital=capital,
        currency=currency,
        risk_profile=risk_profile,
        max_positions=max_positions,
        report_count=len(reports),
    )


def optimize_allocation(
    candidates: Sequence[dict],
    *,
    capital: float,
    currency: str,
    risk_profile: str,
    max_positions: int | None = None,
    report_count: int | None = None,
) -> dict:
    settings = RISK_SETTINGS.get(risk_profile, RISK_SETTINGS["medium"])
    position_limit = max_positions or int(settings["positions"])
    scored = []
    for candidate in candidates:
        if candidate["current_price"] <= 0 or candidate["expected_2d_return"] <= 0:
            continue
        if candidate["data_quality_score"] < settings["min_quality"]:
            continue
        if candidate["up_probability"] < settings["min_probability"]:
            continue
        confidence_factor = {
            "high": 1.0,
            "medium": 0.82,
            "low": 0.55,
        }.get(candidate.get("confidence_level"), 0.55)
        quality_factor = max(0.4, candidate["data_quality_score"] / 100)
        probability_factor = max(0.1, (candidate["up_probability"] - 45) / 40)
        score_factor = max(0.5, candidate["final_score"] / 65)
        volatility_penalty = (
            max(0.65, candidate["annual_volatility"] / 35)
            ** settings["volatility_power"]
        )
        surge_penalty = 0.72 if candidate.get("surge_warning") else 1.0
        overheat_penalty = 0.72 if (candidate.get("rsi") or 0) >= 75 else 1.0
        candidate = dict(candidate)
        candidate["allocation_score"] = (
            candidate["expected_2d_return"]
            * confidence_factor
            * quality_factor
            * probability_factor
            * score_factor
            * surge_penalty
            * overheat_penalty
            / volatility_penalty
        )
        scored.append(candidate)

    scored.sort(key=lambda row: row["allocation_score"], reverse=True)
    selected = _select_diversified(
        scored,
        position_limit,
        float(settings["correlation_penalty"]),
    )
    if not selected:
        return _empty_plan(
            capital,
            currency,
            risk_profile,
            "현재 기준을 통과한 종목이 없습니다. 분석을 갱신하거나 위험 성향을 조정하세요.",
            report_count or len(candidates),
        )

    invest_ratio = float(settings["invest_ratio"])
    max_weight = float(settings["max_weight"])
    raw_weights = {
        row["ticker"]: max(0.001, row["allocation_score"]) for row in selected
    }
    target_weights = _capped_weights(raw_weights, invest_ratio, max_weight)
    investable = capital * invest_ratio
    quantities: dict[str, int] = {}
    amounts: dict[str, float] = {}
    for row in selected:
        target_amount = capital * target_weights[row["ticker"]]
        quantity = max(0, math.floor(target_amount / row["current_price"]))
        quantities[row["ticker"]] = quantity
        amounts[row["ticker"]] = quantity * row["current_price"]

    invested = sum(amounts.values())
    remaining_investable = max(0.0, investable - invested)
    max_position_amount = capital * max_weight
    while True:
        affordable = [
            row
            for row in selected
            if row["current_price"] <= remaining_investable
            and amounts[row["ticker"]] + row["current_price"] <= max_position_amount
        ]
        if not affordable:
            break
        row = max(
            affordable,
            key=lambda item: item["allocation_score"]
            * max(0.2, 1 - amounts[item["ticker"]] / max_position_amount),
        )
        quantities[row["ticker"]] += 1
        amounts[row["ticker"]] += row["current_price"]
        invested += row["current_price"]
        remaining_investable -= row["current_price"]

    allocations = []
    for row in selected:
        quantity = quantities[row["ticker"]]
        amount = amounts[row["ticker"]]
        if quantity <= 0:
            continue
        reason_parts = [
            f"상승 가능성 {row['up_probability']:.1f}%",
            f"DAY 2 대표 기대수익 {row['expected_2d_return']:+.2f}%",
            f"데이터 품질 {row['data_quality_score']:.0f}점",
        ]
        if row.get("surge_warning"):
            reason_parts.append("급등 주의로 비중 감점")
        allocations.append(
            {
                **{key: row[key] for key in (
                    "ticker",
                    "name",
                    "market",
                    "currency",
                    "current_price",
                    "up_probability",
                    "expected_2d_return",
                    "downside_scenario_return",
                    "data_quality_score",
                    "final_score",
                    "annual_volatility",
                    "surge_warning",
                )},
                "quantity": quantity,
                "amount": round(amount, 2),
                "weight": round(amount / capital * 100, 2),
                "reason": " · ".join(reason_parts),
            }
        )

    invested = sum(row["amount"] for row in allocations)
    cash = max(0.0, capital - invested)
    if invested > 0:
        expected_return = sum(
            row["amount"] * row["expected_2d_return"] for row in allocations
        ) / invested
        downside_return = sum(
            row["amount"] * row["downside_scenario_return"] for row in allocations
        ) / invested
        portfolio_volatility = _portfolio_volatility(
            allocations,
            selected,
            invested,
        )
    else:
        expected_return = downside_return = portfolio_volatility = 0.0

    warnings = [
        "예상 수익률은 과거 가격과 현재 신호를 이용한 시뮬레이션이며 수익을 보장하지 않습니다.",
        "실제 주문 전 수수료·세금·환전 비용과 최신 공시를 다시 확인하세요.",
    ]
    if any(row["surge_warning"] for row in allocations):
        warnings.append("급등 주의 종목은 제외하지 않았지만 목표 비중을 감점했습니다.")
    if len(allocations) < 3:
        warnings.append("예산 또는 조건 때문에 분산 종목 수가 적습니다.")

    return {
        "capital": round(capital, 2),
        "currency": currency,
        "risk_profile": risk_profile,
        "invested_amount": round(invested, 2),
        "cash_reserve": round(cash, 2),
        "cash_reserve_rate": round(cash / capital * 100, 2),
        "expected_2d_return": round(expected_return, 2),
        "expected_profit": round(invested * expected_return / 100, 2),
        "downside_scenario_return": round(downside_return, 2),
        "downside_scenario_amount": round(invested * downside_return / 100, 2),
        "estimated_annual_volatility": round(portfolio_volatility, 2),
        "allocations": sorted(
            allocations, key=lambda row: row["amount"], reverse=True
        ),
        "methodology": [
            "최신 리포트의 DAY 2 대표 기대수익과 상승 가능성을 결합",
            "데이터 품질·예측 신뢰도·종합 점수가 낮으면 자동 감점",
            "60거래일 수익률 상관관계가 높은 종목의 동시 편입을 억제",
            f"단일 종목 최대 {max_weight * 100:.0f}%와 현금 완충 {100 - invest_ratio * 100:.0f}% 적용",
            "급등·RSI 과열 종목은 제거하지 않고 추천 비중을 축소",
        ],
        "warnings": warnings,
        "generated_from_reports": report_count or len(candidates),
    }


def _select_diversified(
    rows: Sequence[dict],
    limit: int,
    correlation_penalty: float,
) -> list[dict]:
    selected: list[dict] = []
    remaining = list(rows)
    while remaining and len(selected) < limit:
        if not selected:
            choice = remaining[0]
        else:
            choice = max(
                remaining,
                key=lambda row: row["allocation_score"]
                * (
                    1
                    - correlation_penalty
                    * _average_positive_correlation(row, selected)
                ),
            )
        selected.append(choice)
        remaining.remove(choice)
    return selected


def _average_positive_correlation(candidate: dict, selected: Sequence[dict]) -> float:
    correlations = [
        max(0.0, _correlation(candidate.get("returns", {}), row.get("returns", {})))
        for row in selected
    ]
    return sum(correlations) / len(correlations) if correlations else 0.0


def _correlation(left: dict, right: dict) -> float:
    common = sorted(set(left).intersection(right))
    if len(common) < 15:
        return 0.25
    x = [left[key] for key in common]
    y = [right[key] for key in common]
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    variance_x = sum((a - mean_x) ** 2 for a in x)
    variance_y = sum((b - mean_y) ** 2 for b in y)
    denominator = math.sqrt(variance_x * variance_y)
    return max(-1.0, min(1.0, covariance / denominator)) if denominator else 0.0


def _capped_weights(
    raw_weights: dict[str, float],
    total_weight: float,
    cap: float,
) -> dict[str, float]:
    result = {ticker: 0.0 for ticker in raw_weights}
    active = set(raw_weights)
    remaining = min(total_weight, cap * len(active))
    while active and remaining > 1e-9:
        raw_total = sum(raw_weights[ticker] for ticker in active)
        capped = []
        for ticker in active:
            proposed = remaining * raw_weights[ticker] / raw_total
            if proposed >= cap:
                result[ticker] = cap
                capped.append(ticker)
        if not capped:
            for ticker in active:
                result[ticker] = remaining * raw_weights[ticker] / raw_total
            break
        for ticker in capped:
            remaining -= result[ticker]
            active.remove(ticker)
    return result


def _portfolio_volatility(
    allocations: Sequence[dict],
    selected: Sequence[dict],
    invested: float,
) -> float:
    source = {row["ticker"]: row for row in selected}
    variance = 0.0
    for left in allocations:
        for right in allocations:
            left_weight = left["amount"] / invested
            right_weight = right["amount"] / invested
            correlation = (
                1.0
                if left["ticker"] == right["ticker"]
                else _correlation(
                    source[left["ticker"]].get("returns", {}),
                    source[right["ticker"]].get("returns", {}),
                )
            )
            variance += (
                left_weight
                * right_weight
                * left["annual_volatility"]
                * right["annual_volatility"]
                * correlation
            )
    return math.sqrt(max(0.0, variance))


def _return_series(db: Session, stock_id: int) -> dict[date, float]:
    rows = db.scalars(
        select(DailyPrice)
        .where(
            DailyPrice.stock_id == stock_id,
            DailyPrice.close_price.is_not(None),
        )
        .order_by(DailyPrice.date.desc())
        .limit(70)
    ).all()
    ordered = list(reversed(rows))
    result = {}
    previous = None
    for row in ordered:
        close = float(row.close_price)
        if previous and previous > 0:
            result[row.date] = close / previous - 1
        previous = close
    return result


def _empty_plan(
    capital: float,
    currency: str,
    risk_profile: str,
    warning: str,
    report_count: int = 0,
) -> dict:
    return {
        "capital": round(capital, 2),
        "currency": currency,
        "risk_profile": risk_profile,
        "invested_amount": 0.0,
        "cash_reserve": round(capital, 2),
        "cash_reserve_rate": 100.0,
        "expected_2d_return": 0.0,
        "expected_profit": 0.0,
        "downside_scenario_return": 0.0,
        "downside_scenario_amount": 0.0,
        "estimated_annual_volatility": 0.0,
        "allocations": [],
        "methodology": [],
        "warnings": [warning, "수익을 보장하는 배분은 존재하지 않습니다."],
        "generated_from_reports": report_count,
    }
