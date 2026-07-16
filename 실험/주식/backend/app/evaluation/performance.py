from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


DEFAULT_THRESHOLDS = (0.55, 0.60, 0.65, 0.70, 0.75, 0.80)


def select_confidence_threshold(
    targets: np.ndarray,
    probabilities: np.ndarray,
    actual_returns: np.ndarray,
    *,
    transaction_cost_percent: float = 0.20,
    minimum_signals: int = 150,
    thresholds: Iterable[float] = DEFAULT_THRESHOLDS,
) -> dict:
    """Select a threshold using calibration data only."""
    candidates = [
        selective_signal_metrics(
            targets,
            probabilities,
            actual_returns,
            threshold=threshold,
            transaction_cost_percent=transaction_cost_percent,
        )
        for threshold in thresholds
    ]
    eligible = [row for row in candidates if row["trades"] >= minimum_signals]
    if eligible:
        selected = max(
            eligible,
            key=lambda row: (
                row["accuracy"] or 0,
                row["average_net_return"] or -999,
                row["signal_frequency"] or 0,
            ),
        )
    else:
        selected = min(
            candidates,
            key=lambda row: abs(row["threshold"] - 0.60),
        )
    return {
        "selected_threshold": selected["threshold"],
        "minimum_signals": minimum_signals,
        "selection_source": "calibration_only",
        "candidates": candidates,
    }


def selective_signal_metrics(
    targets: np.ndarray,
    probabilities: np.ndarray,
    actual_returns: np.ndarray,
    *,
    threshold: float,
    transaction_cost_percent: float = 0.20,
) -> dict:
    targets = np.asarray(targets, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    actual_returns = np.asarray(actual_returns, dtype=float)
    confidence = np.maximum(probabilities, 1 - probabilities)
    selected = confidence >= threshold
    if not selected.any():
        return _empty_signal_metrics(threshold)

    predicted_direction = np.where(probabilities[selected] >= 0.5, 1, -1)
    actual_direction = np.where(targets[selected] == 1, 1, -1)
    gross_returns = predicted_direction * actual_returns[selected]
    net_returns = gross_returns - transaction_cost_percent
    wins = net_returns > 0
    losses = net_returns < 0
    cumulative_curve = np.cumprod(1 + np.clip(net_returns, -99.0, 1000.0) / 100)
    running_peak = np.maximum.accumulate(cumulative_curve)
    drawdown = (cumulative_curve / running_peak - 1) * 100
    std = float(np.std(net_returns, ddof=1)) if len(net_returns) > 1 else 0.0
    downside = net_returns[net_returns < 0]
    downside_std = (
        float(np.std(downside, ddof=1)) if len(downside) > 1 else 0.0
    )
    annualizer = math.sqrt(252)
    average_win = float(net_returns[wins].mean()) if wins.any() else None
    average_loss = float(abs(net_returns[losses].mean())) if losses.any() else None
    return {
        "threshold": round(float(threshold), 2),
        "trades": int(selected.sum()),
        "signal_frequency": _round(selected.mean() * 100, 3),
        "accuracy": _round((predicted_direction == actual_direction).mean() * 100, 3),
        "win_rate": _round(wins.mean() * 100, 3),
        "average_gross_return": _round(gross_returns.mean(), 4),
        "average_net_return": _round(net_returns.mean(), 4),
        "cumulative_net_return": _round((cumulative_curve[-1] - 1) * 100, 3),
        "maximum_drawdown": _round(float(drawdown.min()), 3),
        "payoff_ratio": (
            _round(average_win / average_loss, 4)
            if average_win is not None and average_loss
            else None
        ),
        "sharpe": _round(net_returns.mean() / std * annualizer, 4) if std else None,
        "sortino": (
            _round(net_returns.mean() / downside_std * annualizer, 4)
            if downside_std
            else None
        ),
        "transaction_cost_percent": transaction_cost_percent,
    }


def meaningful_move_metrics(
    actual_returns: np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_move_percent: float = 1.0,
) -> dict:
    returns = np.asarray(actual_returns, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    selected = np.abs(returns) >= minimum_move_percent
    if not selected.any():
        return {"samples": 0, "accuracy": None, "minimum_move_percent": minimum_move_percent}
    predicted = probabilities[selected] >= 0.5
    actual = returns[selected] > 0
    return {
        "samples": int(selected.sum()),
        "accuracy": _round((predicted == actual).mean() * 100, 3),
        "minimum_move_percent": minimum_move_percent,
    }


def segment_metrics(
    labels: np.ndarray,
    targets: np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_samples: int = 30,
) -> list[dict]:
    labels = np.asarray(labels, dtype=object)
    targets = np.asarray(targets, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    result = []
    for label in sorted({str(value) for value in labels}):
        mask = labels.astype(str) == label
        if mask.sum() < minimum_samples:
            continue
        predicted = probabilities[mask] >= 0.5
        result.append(
            {
                "segment": label,
                "samples": int(mask.sum()),
                "accuracy": _round((predicted == targets[mask]).mean() * 100, 3),
                "mean_probability": _round(probabilities[mask].mean() * 100, 3),
                "observed_up_rate": _round(targets[mask].mean() * 100, 3),
            }
        )
    return result


def _empty_signal_metrics(threshold: float) -> dict:
    return {
        "threshold": round(float(threshold), 2),
        "trades": 0,
        "signal_frequency": 0.0,
        "accuracy": None,
        "win_rate": None,
        "average_gross_return": None,
        "average_net_return": None,
        "cumulative_net_return": None,
        "maximum_drawdown": None,
        "payoff_ratio": None,
        "sharpe": None,
        "sortino": None,
        "transaction_cost_percent": None,
    }


def _round(value: float, digits: int) -> float:
    return round(float(value), digits)
