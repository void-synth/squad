"""
Composite risk scoring: velocity (50%), graph hub (30%), metadata (20%).

Velocity dominates because rapid structural changes in account behaviour are
strong early signals. Graph structure catches orchestration. Metadata adds
context but is noisier alone, so it gets the smallest weight.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.ai.graph_engine import transaction_graph
from app.ai.nlp_analyser import metadata_analyser
from app.ai.velocity_detector import velocity_detector

_SENDER_RECENT: dict[str, list[float]] = defaultdict(list)
_RECEIVERS_TODAY: dict[str, set[str]] = defaultdict(set)
_RECEIVER_FIRST_SEEN: dict[str, float] = {}


def _today_key(sender: str) -> str:
    d = datetime.now(timezone.utc).date().isoformat()
    return f"{sender}:{d}"


def _prune_sender_recent(sender: str, now: float) -> None:
    hour_ago = now - 3600
    _SENDER_RECENT[sender] = [t for t in _SENDER_RECENT[sender] if t >= hour_ago]


def _record_after_analysis(transaction: dict[str, Any]) -> None:
    now = time.time()
    sender = transaction["sender_account"]
    receiver = transaction["receiver_account"]
    _prune_sender_recent(sender, now)
    _SENDER_RECENT[sender].append(now)
    _RECEIVERS_TODAY[_today_key(sender)].add(receiver)
    if receiver not in _RECEIVER_FIRST_SEEN:
        _RECEIVER_FIRST_SEEN[receiver] = now


class RiskEngine:
    def __init__(self) -> None:
        self.velocity = velocity_detector
        self.graph = transaction_graph
        self.metadata = metadata_analyser

    def build_velocity_features(
        self, transaction: dict[str, Any], account_profile: dict[str, Any] | None
    ) -> dict[str, Any]:
        profile = account_profile or {}
        amount = float(transaction.get("amount", 0) or 0)
        avg = float(profile.get("avg_transaction_amount") or 0)
        if avg > 0:
            ratio = amount / avg
        else:
            ratio = 1.0

        sender = transaction["sender_account"]
        receiver = transaction["receiver_account"]
        now = time.time()
        _prune_sender_recent(sender, now)
        five_min = now - 300
        hour_ago = now - 3600
        txs_5m = sum(1 for t in _SENDER_RECENT[sender] if t >= five_min)
        txs_1h = sum(1 for t in _SENDER_RECENT[sender] if t >= hour_ago)
        unique_recv = len(_RECEIVERS_TODAY[_today_key(sender)])

        is_new_receiver = int(bool(transaction.get("receiver_is_new", False)))

        amt_int = int(amount)
        round_amount_flag = 1 if amt_int > 0 and amt_int % 100000 == 0 else 0

        return {
            "amount_to_avg_ratio": float(min(max(ratio, 0.0), 500.0)),
            "transactions_last_5_minutes": int(txs_5m),
            "transactions_last_1_hour": int(txs_1h),
            "unique_receivers_today": int(max(unique_recv, 0)),
            "is_new_receiver": int(is_new_receiver),
            "round_amount_flag": int(round_amount_flag),
        }

    def format_reason(
        self,
        velocity_reason: str,
        graph_score: float,
        metadata_reason: str,
        final_score: float,
    ) -> str:
        graph_bit = ""
        if graph_score >= 0.6:
            graph_bit = " Sender sits on a high betweenness hub in the transfer graph."
        elif graph_score >= 0.3:
            graph_bit = " Sender shows elevated network centrality."
        meta_bit = f" {metadata_reason}" if metadata_reason else ""
        return (
            f"{velocity_reason}{graph_bit}{meta_bit} Risk Score: {final_score * 100:.0f}%."
        ).strip()

    def analyse(self, transaction: dict[str, Any], account_profile: dict[str, Any] | None) -> dict[str, Any]:
        vfeat = self.build_velocity_features(transaction, account_profile)
        velocity_raw = float(self.velocity.predict(vfeat))
        velocity_reason = self.velocity.get_reason(vfeat)

        ts = datetime.now(timezone.utc).isoformat()
        self.graph.add_transaction(
            transaction["sender_account"],
            transaction["receiver_account"],
            float(transaction.get("amount", 0) or 0),
            ts,
        )
        graph_raw = float(self.graph.get_risk_score(transaction["sender_account"]))

        meta_raw, meta_reason = self.metadata.combined_score(
            str(transaction.get("description", "")),
            float(transaction.get("amount", 0) or 0),
            str(transaction.get("device_id", "")),
            str(transaction.get("sender_account", "")),
        )

        final_score = velocity_raw * 0.5 + graph_raw * 0.3 + meta_raw * 0.2
        final_score = float(max(0.0, min(1.0, final_score)))

        if final_score < 0.75:
            alert_level = 0
            recommended_action = "safe"
        elif final_score < 0.85:
            alert_level = 2
            recommended_action = "monitor"
        else:
            alert_level = 3
            recommended_action = "hold"

        pattern_type = "combined"
        if velocity_raw >= graph_raw and velocity_raw >= meta_raw:
            if vfeat["amount_to_avg_ratio"] > 15 or vfeat["transactions_last_5_minutes"] > 2:
                pattern_type = "smurfing" if vfeat["unique_receivers_today"] > 3 else "velocity_spike"
        if graph_raw >= velocity_raw and graph_raw >= meta_raw and graph_raw >= 0.35:
            pattern_type = "graph_hub"
        if meta_raw >= velocity_raw and meta_raw >= graph_raw and meta_raw >= 0.25:
            pattern_type = "device_sharing" if "device" in meta_reason.lower() else "combined"

        reason = self.format_reason(velocity_reason, graph_raw, meta_reason, final_score)

        _record_after_analysis(transaction)

        return {
            "final_score": final_score,
            "alert_level": alert_level,
            "velocity_score": velocity_raw,
            "graph_score": graph_raw,
            "metadata_score": meta_raw,
            "reason": reason,
            "pattern_type": pattern_type,
            "recommended_action": recommended_action,
        }


risk_engine = RiskEngine()
