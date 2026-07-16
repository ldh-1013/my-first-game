from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailyPrice, Stock
from app.services.prediction_engine import RuleBasedPredictionModel
from app.services.quality_service import surge_status
from app.services.recommendation_engine import _top5_score
from app.services.scoring_engine import (
    calculate_final_score,
    calculate_risk_score,
    calculate_technical_score,
    calculate_volume_score,
)


def rank_global_market(db: Session, limit: int = 5) -> list[dict]:
    """Rank all locally collected KR/US listed stocks, independent of user holdings."""
    stocks = db.scalars(
        select(Stock).where(
            Stock.is_listed.is_(True),
            Stock.market.in_(["KR", "US"]),
        )
    ).all()
    ranked: list[dict] = []
    minimum_date = date.today() - timedelta(days=10)

    for stock in stocks:
        prices = db.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == stock.id,
                DailyPrice.close_price.is_not(None),
            )
            .order_by(DailyPrice.date.desc())
            .limit(60)
        ).all()
        if len(prices) < 20 or prices[0].date < minimum_date:
            continue

        latest_row = prices[0]
        oldest_for_return = prices[min(5, len(prices) - 1)]
        recent_5d_return = (
            ((latest_row.close_price / oldest_for_return.close_price) - 1) * 100
            if latest_row.close_price and oldest_for_return.close_price
            else 0
        )
        latest = {
            "close": latest_row.close_price,
            "ma5": latest_row.ma5,
            "ma20": latest_row.ma20,
            "ma60": latest_row.ma60,
            "rsi": latest_row.rsi,
            "change_rate": latest_row.change_rate,
            "volatility_20d": latest_row.volatility_20d,
            "volume_change_rate": latest_row.volume_change_rate,
            "recent_5d_return": recent_5d_return,
        }
        technical_score = calculate_technical_score(latest)
        volume_score = calculate_volume_score(latest)
        risk_score = calculate_risk_score(latest, has_news=True, is_listed=True)
        final_score = calculate_final_score(
            news_score=0,
            technical_score=technical_score,
            volume_score=volume_score,
            financial_score=0,
            industry_macro_score=0,
            risk_score=risk_score,
            weights={
                "news": 0,
                "technical": 0.55,
                "volume": 0.35,
                "financial": 0,
                "industry_macro": 0.10,
                "risk_penalty": 0.08,
            },
        )
        prediction = RuleBasedPredictionModel().predict(
            final_score=final_score,
            volatility=latest_row.volatility_20d,
            data_points=len(prices),
        )
        warning, warning_reason = surge_status(latest)
        ranking_score = _top5_score(
            prediction["up_probability"],
            prediction["expected_range_high"],
        )
        ranked.append(
            {
                "stock": stock,
                "latest_date": latest_row.date,
                "final_score": final_score,
                "ranking_score": round(ranking_score, 1),
                "up_probability": prediction["up_probability"],
                "expected_range_low": prediction["expected_range_low"],
                "expected_range_high": prediction["expected_range_high"],
                "risk_score": risk_score,
                "surge_warning": warning,
                "surge_reason": warning_reason,
                "recent_5d_return": round(recent_5d_return, 2),
                "technical_score": technical_score,
                "volume_score": volume_score,
            }
        )

    ranked.sort(
        key=lambda row: (
            row["ranking_score"],
            row["up_probability"],
            row["final_score"],
        ),
        reverse=True,
    )
    return ranked[:limit]
