from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss


def fit_regime_weights(
    targets: np.ndarray,
    component_probabilities: dict[str, np.ndarray],
    regimes: np.ndarray,
    *,
    minimum_segment_samples: int = 100,
) -> dict[str, dict[str, float]]:
    """Fit inverse-Brier weights on calibration data only."""
    targets = np.asarray(targets, dtype=int)
    regimes = np.asarray(regimes, dtype=object)
    weights = {
        "global": _inverse_brier_weights(targets, component_probabilities),
    }
    for regime in sorted({str(value) for value in regimes}):
        mask = regimes.astype(str) == regime
        if mask.sum() < minimum_segment_samples:
            continue
        weights[regime] = _inverse_brier_weights(
            targets[mask],
            {name: values[mask] for name, values in component_probabilities.items()},
        )
    return weights


def combine_probabilities(
    component_probabilities: dict[str, np.ndarray],
    regimes: np.ndarray,
    regime_weights: dict[str, dict[str, float]],
) -> np.ndarray:
    regimes = np.asarray(regimes, dtype=object)
    result = np.zeros(len(regimes), dtype=float)
    global_weights = regime_weights["global"]
    for index, regime in enumerate(regimes.astype(str)):
        weights = regime_weights.get(regime, global_weights)
        result[index] = sum(
            weights.get(name, 0.0) * float(values[index])
            for name, values in component_probabilities.items()
        )
    return np.clip(result, 1e-5, 1 - 1e-5)


def combine_one(
    component_probabilities: dict[str, float],
    regime: str,
    regime_weights: dict[str, dict[str, float]],
) -> float:
    weights = regime_weights.get(regime, regime_weights["global"])
    return float(
        np.clip(
            sum(
                weights.get(name, 0.0) * float(probability)
                for name, probability in component_probabilities.items()
            ),
            1e-5,
            1 - 1e-5,
        )
    )


def _inverse_brier_weights(
    targets: np.ndarray,
    component_probabilities: dict[str, np.ndarray],
) -> dict[str, float]:
    raw = {}
    for name, probabilities in component_probabilities.items():
        score = brier_score_loss(targets, np.clip(probabilities, 1e-5, 1 - 1e-5))
        raw[name] = 1 / max(score, 1e-6)
    total = sum(raw.values()) or 1.0
    return {name: value / total for name, value in raw.items()}
