import math
from abc import ABC, abstractmethod


class BasePredictionModel(ABC):
    @abstractmethod
    def predict(self, final_score: float, volatility: float | None, data_points: int) -> dict:
        raise NotImplementedError


class RuleBasedPredictionModel(BasePredictionModel):
    version = "rule-based-v2-calibrated"

    @staticmethod
    def score_to_probability(final_score: float) -> float:
        return 1 / (1 + math.exp(-(final_score - 50) / 12))

    def predict(self, final_score: float, volatility: float | None, data_points: int) -> dict:
        up_probability = self.score_to_probability(final_score) * 100
        daily_volatility = ((volatility or 25) / math.sqrt(252)) if volatility is not None else 2.5
        directional_bias = (up_probability - 50) / 20
        expected_low = -max(0.5, daily_volatility * 1.15 - directional_bias)
        expected_high = max(0.5, daily_volatility * 1.15 + directional_bias)

        if data_points >= 60 and volatility is not None:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "up_probability": round(up_probability, 1),
            "down_probability": round(100 - up_probability, 1),
            "expected_range_low": round(expected_low, 2),
            "expected_range_high": round(expected_high, 2),
            "confidence_level": confidence,
            "model_version": self.version,
        }
