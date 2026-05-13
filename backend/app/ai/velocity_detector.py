"""
Velocity and anomaly detection using IsolationForest.

Trains on synthetic Nigerian-like transaction features; flags outliers
as higher fraud scores (closer to 1.0).
"""

from __future__ import annotations

import random
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def load_training_data() -> pd.DataFrame:
    """Generate synthetic training data (normal + seeded fraud rows)."""
    random.seed(42)
    np.random.seed(42)
    rows: list[dict[str, Any]] = []

    for _ in range(9500):
        rows.append(
            {
                "amount_to_avg_ratio": float(np.random.uniform(0.1, 3.0)),
                "transactions_last_5_minutes": int(np.random.randint(0, 3)),
                "transactions_last_1_hour": int(np.random.randint(0, 6)),
                "unique_receivers_today": int(np.random.randint(1, 4)),
                "is_new_receiver": int(np.random.choice([0, 1], p=[0.9, 0.1])),
                "round_amount_flag": int(np.random.choice([0, 1], p=[0.85, 0.15])),
            }
        )

    for _ in range(500):
        rows.append(
            {
                "amount_to_avg_ratio": float(np.random.uniform(50.0, 120.0)),
                "transactions_last_5_minutes": int(np.random.randint(4, 12)),
                "transactions_last_1_hour": int(np.random.randint(8, 30)),
                "unique_receivers_today": int(np.random.randint(5, 15)),
                "is_new_receiver": 1,
                "round_amount_flag": 1,
            }
        )

    df = pd.DataFrame(rows)
    return df.sample(frac=1.0, random_state=42).reset_index(drop=True)


FEATURE_COLUMNS = [
    "amount_to_avg_ratio",
    "transactions_last_5_minutes",
    "transactions_last_1_hour",
    "unique_receivers_today",
    "is_new_receiver",
    "round_amount_flag",
]


class VelocityDetector:
    def __init__(self) -> None:
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self._min_score: float = 0.0
        self._max_score: float = 1.0
        self._trained = False

    def train(self) -> None:
        df = load_training_data()
        X = df[FEATURE_COLUMNS].values
        self.model.fit(X)
        train_scores = self.model.score_samples(X)
        self._min_score = float(train_scores.min())
        self._max_score = float(train_scores.max())
        self._trained = True

    def predict(self, transaction_features: dict[str, Any]) -> float:
        """Return fraud-like score 0..1 (higher = more suspicious)."""
        if not self._trained:
            self.train()
        vec = np.array([[float(transaction_features[k]) for k in FEATURE_COLUMNS]])
        s = float(self.model.score_samples(vec)[0])
        span = self._max_score - self._min_score + 1e-9
        norm = (s - self._min_score) / span
        fraud = 1.0 - norm
        return float(max(0.0, min(1.0, fraud)))

    def get_reason(self, transaction_features: dict[str, Any]) -> str:
        parts: list[str] = []
        r = float(transaction_features["amount_to_avg_ratio"])
        if r > 10:
            parts.append(f"transfer is ~{r:.0f}x the account's typical size")
        if int(transaction_features["transactions_last_5_minutes"]) > 2:
            parts.append("unusually high velocity in the last 5 minutes")
        if int(transaction_features["unique_receivers_today"]) > 3:
            parts.append("many distinct receivers today")
        if int(transaction_features["is_new_receiver"]):
            parts.append("receiver looks newly active")
        if int(transaction_features["round_amount_flag"]):
            parts.append("round-amount structuring pattern")
        if not parts:
            return "Velocity profile deviates from the account baseline."
        return "Velocity anomaly: " + "; ".join(parts) + "."


velocity_detector = VelocityDetector()
velocity_detector.train()
