from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.market_regime.classifier import classify_market_regime
from app.models import DailyPrice, Stock


POINT_IN_TIME_FEATURES = [
    "recent_5d_return",
    "recent_20d_return",
    "ma5_gap",
    "ma20_gap",
    "atr_percent",
    "volume_change_rate",
    "log_trading_value",
    "liquidity_percentile",
    "relative_strength_5d",
    "market_return_1d",
    "market_return_20d",
    "market_breadth",
    "market_volatility",
    "regime_bull",
    "regime_bear",
    "regime_sideways",
    "regime_high_vol",
]


def build_point_in_time_feature_map(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> dict[tuple[int, date], dict]:
    warmup = start_date - timedelta(days=100)
    rows = db.execute(
        select(
            DailyPrice.stock_id,
            DailyPrice.date,
            DailyPrice.close_price,
            DailyPrice.volume,
            DailyPrice.trading_value,
            DailyPrice.ma5,
            DailyPrice.ma20,
            DailyPrice.atr,
            DailyPrice.volatility_20d,
            DailyPrice.volume_change_rate,
            Stock.market,
        )
        .join(Stock, Stock.id == DailyPrice.stock_id)
        .where(
            DailyPrice.date >= warmup,
            DailyPrice.date <= end_date,
            DailyPrice.close_price.is_not(None),
        )
        .order_by(DailyPrice.stock_id.asc(), DailyPrice.date.asc())
    ).all()
    if not rows:
        return {}
    frame = pd.DataFrame(
        rows,
        columns=[
            "stock_id",
            "date",
            "close",
            "volume",
            "trading_value",
            "ma5",
            "ma20",
            "atr",
            "volatility_20d",
            "volume_change_rate",
            "market",
        ],
    )
    frame = frame.sort_values(["stock_id", "date"])
    grouped = frame.groupby("stock_id", sort=False)
    frame["return_1d"] = grouped["close"].pct_change() * 100
    frame["recent_5d_return"] = grouped["close"].pct_change(5) * 100
    frame["recent_20d_return"] = grouped["close"].pct_change(20) * 100
    frame["ma5_gap"] = (frame["close"] / frame["ma5"] - 1) * 100
    frame["ma20_gap"] = (frame["close"] / frame["ma20"] - 1) * 100
    frame["atr_percent"] = frame["atr"] / frame["close"] * 100
    trading_value = frame["trading_value"].where(
        frame["trading_value"].notna(),
        frame["close"] * frame["volume"],
    )
    frame["log_trading_value"] = np.log1p(trading_value.clip(lower=0))
    market_date = frame.groupby(["market", "date"], sort=False)
    frame["liquidity_percentile"] = market_date["log_trading_value"].rank(
        pct=True,
        method="average",
    )
    aggregates = market_date.agg(
        market_return_1d=("return_1d", "mean"),
        market_return_20d=("recent_20d_return", "mean"),
        market_breadth=("return_1d", lambda values: float((values > 0).mean())),
        market_volatility=("volatility_20d", "mean"),
        market_return_5d=("recent_5d_return", "mean"),
    ).reset_index()
    frame = frame.merge(aggregates, on=["market", "date"], how="left")
    frame["relative_strength_5d"] = (
        frame["recent_5d_return"] - frame["market_return_5d"]
    )
    frame["market_regime"] = frame.apply(
        lambda row: classify_market_regime(
            row["market_return_20d"],
            row["market_breadth"],
            row["market_volatility"],
        ),
        axis=1,
    )
    frame = frame[frame["date"] >= start_date]
    result: dict[tuple[int, date], dict] = {}
    for row in frame.itertuples(index=False):
        regime = row.market_regime
        result[(int(row.stock_id), row.date)] = {
            "recent_5d_return": _finite(row.recent_5d_return),
            "recent_20d_return": _finite(row.recent_20d_return),
            "ma5_gap": _finite(row.ma5_gap),
            "ma20_gap": _finite(row.ma20_gap),
            "atr_percent": _finite(row.atr_percent),
            "volume_change_rate": _finite(row.volume_change_rate),
            "log_trading_value": _finite(row.log_trading_value),
            "liquidity_percentile": _finite(row.liquidity_percentile),
            "relative_strength_5d": _finite(row.relative_strength_5d),
            "market_return_1d": _finite(row.market_return_1d),
            "market_return_20d": _finite(row.market_return_20d),
            "market_breadth": _finite(row.market_breadth),
            "market_volatility": _finite(row.market_volatility),
            "market_regime": regime,
            "regime_bull": float(regime.startswith("bull")),
            "regime_bear": float(regime.startswith("bear")),
            "regime_sideways": float(regime.startswith("sideways")),
            "regime_high_vol": float(regime.endswith("high_vol")),
        }
    return result


def live_point_in_time_features(
    db: Session,
    *,
    stock_id: int,
    market: str,
    as_of_date: date,
) -> dict:
    feature_map = build_point_in_time_feature_map(
        db,
        start_date=as_of_date,
        end_date=as_of_date,
    )
    return feature_map.get(
        (stock_id, as_of_date),
        {
            key: np.nan for key in POINT_IN_TIME_FEATURES
        }
        | {
            "market_regime": "sideways_low_vol",
            "regime_bull": 0.0,
            "regime_bear": 0.0,
            "regime_sideways": 1.0,
            "regime_high_vol": 0.0,
            "market": market,
        },
    )


def _finite(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan
