from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import DailyPrice, Holding


def portfolio_summary(db: Session) -> dict:
    holdings = db.scalars(
        select(Holding)
        .options(joinedload(Holding.stock))
        .where(Holding.is_active.is_(True))
    ).all()
    positions = []
    currency_totals: dict[str, dict[str, float]] = {}
    for holding in holdings:
        latest = db.scalar(
            select(DailyPrice)
            .where(DailyPrice.stock_id == holding.stock_id, DailyPrice.close_price.is_not(None))
            .order_by(DailyPrice.date.desc())
        )
        current_price = latest.close_price if latest else None
        cost = holding.avg_buy_price * holding.quantity
        value = current_price * holding.quantity if current_price is not None else None
        pnl = value - cost if value is not None else None
        pnl_rate = (pnl / cost * 100) if pnl is not None and cost > 0 else None
        totals = currency_totals.setdefault(holding.currency, {"cost": 0.0, "value": 0.0})
        totals["cost"] += cost
        totals["value"] += value or 0
        positions.append(
            {
                "holding_id": holding.id,
                "ticker": holding.stock.ticker,
                "name": holding.stock.name,
                "market": holding.market_type,
                "currency": holding.currency,
                "quantity": holding.quantity,
                "avg_buy_price": holding.avg_buy_price,
                "current_price": current_price,
                "cost": round(cost, 2),
                "value": round(value, 2) if value is not None else None,
                "pnl": round(pnl, 2) if pnl is not None else None,
                "pnl_rate": round(pnl_rate, 2) if pnl_rate is not None else None,
                "weight": 0.0,
                "risk_tolerance": holding.risk_tolerance,
            }
        )
    for position in positions:
        currency_value = currency_totals[position["currency"]]["value"]
        position["weight"] = (
            round((position["value"] or 0) / currency_value * 100, 2) if currency_value else 0
        )
    concentration = max((position["weight"] for position in positions), default=0)
    summaries = []
    for currency, totals in currency_totals.items():
        pnl = totals["value"] - totals["cost"]
        summaries.append(
            {
                "currency": currency,
                "total_cost": round(totals["cost"], 2),
                "total_value": round(totals["value"], 2),
                "total_pnl": round(pnl, 2),
                "total_pnl_rate": round(pnl / totals["cost"] * 100, 2)
                if totals["cost"]
                else None,
            }
        )
    return {
        "currency_summaries": summaries,
        "mixed_currencies": len(summaries) > 1,
        "largest_position_weight": concentration,
        "concentration_warning": concentration >= 40,
        "positions": sorted(positions, key=lambda row: row["weight"], reverse=True),
    }
