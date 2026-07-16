from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.evaluation.performance import (
    meaningful_move_metrics,
    segment_metrics,
    select_confidence_threshold,
    selective_signal_metrics,
)
from app.models import Stock
from app.services.ml_model_service import (
    build_ml_dataset,
    chronological_split,
    classification_metrics,
)


def performance_diagnostics(db: Session) -> dict:
    frame, metadata = build_ml_dataset(db)
    if frame.empty:
        return {
            "status": "insufficient",
            "methodology": _methodology(metadata),
            "overall": {},
            "periods": [],
            "segments": {},
            "selective_signal": {},
            "data_quality": _data_quality(metadata, frame),
            "leakage_audit": _leakage_audit(),
        }

    frame = frame.sort_values(["prediction_date", "stock_id"]).reset_index(drop=True)
    targets = frame["direction_target"].to_numpy()
    probabilities = frame["baseline_probability"].to_numpy()
    returns = frame["return_target"].to_numpy()
    overall = classification_metrics(targets, probabilities) | {
        "meaningful_move": meaningful_move_metrics(returns, probabilities),
    }
    split = chronological_split(frame)
    calibration = split["calibration"]
    test = split["test"]
    threshold_selection = select_confidence_threshold(
        calibration["direction_target"].to_numpy(),
        calibration["baseline_probability"].to_numpy(),
        calibration["return_target"].to_numpy(),
    )
    threshold = threshold_selection["selected_threshold"]
    selective = selective_signal_metrics(
        test["direction_target"].to_numpy(),
        test["baseline_probability"].to_numpy(),
        test["return_target"].to_numpy(),
        threshold=threshold,
    ) | {
        "selection": threshold_selection,
        "evaluation_source": "held_out_test",
    }
    latest = pd.Timestamp(frame["prediction_date"].max())
    periods = []
    for label, offset in [
        ("1개월", pd.DateOffset(months=1)),
        ("3개월", pd.DateOffset(months=3)),
        ("6개월", pd.DateOffset(months=6)),
        ("1년", pd.DateOffset(years=1)),
        ("전체", None),
    ]:
        current = (
            frame
            if offset is None
            else frame[pd.to_datetime(frame["prediction_date"]) >= latest - offset]
        )
        periods.append(_period_row(label, current))

    volatility = pd.cut(
        frame["volatility_20d"],
        bins=[-np.inf, 25, 45, 70, np.inf],
        labels=["낮음(≤25)", "보통(25~45)", "높음(45~70)", "매우 높음(>70)"],
    ).astype("object").fillna("자료 없음")
    liquidity = pd.cut(
        frame["liquidity_percentile"],
        bins=[-np.inf, 0.2, 0.5, 0.8, np.inf],
        labels=["하위 20%", "20~50%", "50~80%", "상위 20%"],
    ).astype("object").fillna("자료 없음")
    stock_ids = [int(stock_id) for stock_id in frame["stock_id"].unique()]
    stocks = {
        stock.id: stock
        for stock in db.scalars(select(Stock).where(Stock.id.in_(stock_ids))).all()
    }
    stock_labels = frame["stock_id"].map(
        lambda stock_id: (
            f"{stocks[stock_id].name} ({stocks[stock_id].ticker})"
            if stock_id in stocks
            else str(stock_id)
        )
    )
    by_stock = segment_metrics(
        stock_labels.to_numpy(),
        targets,
        probabilities,
        minimum_samples=100,
    )
    return {
        "status": "ready",
        "as_of_date": latest.date(),
        "methodology": _methodology(metadata),
        "overall": overall,
        "periods": periods,
        "segments": {
            "market": segment_metrics(
                frame["market"].to_numpy(),
                targets,
                probabilities,
            ),
            "market_regime": segment_metrics(
                frame["market_regime"].fillna("자료 없음").to_numpy(),
                targets,
                probabilities,
            ),
            "volatility": segment_metrics(
                volatility.to_numpy(),
                targets,
                probabilities,
            ),
            "liquidity": segment_metrics(
                liquidity.to_numpy(),
                targets,
                probabilities,
            ),
            "stocks_best": sorted(
                by_stock,
                key=lambda row: row["accuracy"],
                reverse=True,
            )[:10],
            "stocks_worst": sorted(
                by_stock,
                key=lambda row: row["accuracy"],
            )[:10],
        },
        "selective_signal": selective,
        "data_quality": _data_quality(metadata, frame),
        "leakage_audit": _leakage_audit(),
        "available_features": {
            "technical": True,
            "volume_liquidity": True,
            "market_regime": True,
            "relative_strength": True,
            "historical_news_point_in_time": bool(
                frame["historical_news_available"].mean() > 0
            ),
            "historical_financial_point_in_time": bool(
                frame["historical_financial_available"].mean() > 0
            ),
            "investor_flow": False,
            "sector_industry": False,
        },
    }


def _period_row(label: str, frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"period": label, "samples": 0, "accuracy": None}
    metrics = classification_metrics(
        frame["direction_target"].to_numpy(),
        frame["baseline_probability"].to_numpy(),
    )
    return {
        "period": label,
        "samples": metrics["samples"],
        "accuracy": metrics["accuracy"],
        "brier_score": metrics["brier_score"],
        "expected_calibration_error": metrics["expected_calibration_error"],
    }


def _methodology(metadata: dict) -> dict:
    return {
        "prediction_timing": "거래일 D 종가까지의 정보로 D+1 거래일 종가 방향을 예측",
        "target": "D 종가 대비 다음 실제 거래일 종가 수익률",
        "intraday_prices_used": False,
        "market_regime_basis": "저장된 분석 유니버스의 시장별 평균을 사용한 대용치",
        "flat_handling": "수익률 0% 표본은 방향 정확도에서 제외하되 전체 표본 수에 별도 기록",
        "all_sample_count": metadata.get("total_historical_rows", 0),
        "direction_sample_count": metadata.get("usable_direction_rows", 0),
        "flat_excluded": metadata.get("flat_excluded", 0),
        "invalid_snapshot_excluded": metadata.get(
            "invalid_feature_snapshot_excluded",
            0,
        ),
        "return_curve_note": "누적수익·MDD는 동시 보유 포트폴리오가 아닌 신호 순차 체결 가정의 진단값",
    }


def _data_quality(metadata: dict, frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"metadata": metadata}
    return {
        "metadata": metadata,
        "historical_news_coverage_percent": round(
            float(frame["historical_news_available"].mean() * 100),
            2,
        ),
        "historical_financial_coverage_percent": round(
            float(frame["historical_financial_available"].mean() * 100),
            2,
        ),
        "liquidity_feature_coverage_percent": round(
            float(frame["liquidity_percentile"].notna().mean() * 100),
            2,
        ),
        "regime_feature_coverage_percent": round(
            float(frame["market_regime"].notna().mean() * 100),
            2,
        ),
    }


def _leakage_audit() -> list[dict]:
    return [
        {
            "item": "미래 가격·수익률 입력 차단",
            "status": "pass",
            "evidence": "명시적 특징 화이트리스트와 예측일 이하 가격만 사용",
        },
        {
            "item": "기술지표 시점",
            "status": "pass",
            "evidence": "예측일을 포함한 과거 자료의 이동·누적 계산만 사용",
        },
        {
            "item": "뉴스 게시 시각",
            "status": "limited",
            "evidence": "과거 재현 표본의 시점 일치 뉴스 보급률이 낮아 기본 학습 특징에서 결측 처리",
        },
        {
            "item": "재무 공시 발표 시각·정정 이력",
            "status": "limited",
            "evidence": "as_of_date는 있으나 정정 전 원문 이력 보장이 없어 시점 일치 표본만 사용",
        },
        {
            "item": "수집 시각과 게시 시각 구분",
            "status": "limited",
            "evidence": "뉴스는 published_at과 created_at을 구분하지만 전체 공급원에서 완전하지 않음",
        },
        {
            "item": "최종 시험 자료 자동 재학습 차단",
            "status": "pass",
            "evidence": "학습 15개월·보정 3개월·최종 시험 6개월을 시간순으로 고정하고 자동 활성화하지 않음",
        },
    ]
