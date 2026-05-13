"""
NLP / metadata heuristics for fraud cues.

We look at patterns across many transactions (shared memos, shared devices)
because a single memo is rarely conclusive — coordinated behaviour shows up
only in aggregate.
"""

from __future__ import annotations

import re
from collections import defaultdict

# Regex / keyword clusters common in suspicious flows
SUSPICIOUS_MEMO_PATTERNS = [
    re.compile(r"^\s*$", re.I),
    re.compile(r"^(transfer|payment|send|sent|cash)\s*$", re.I),
    re.compile(r"^(code|ref)\s*:\s*\w+", re.I),
]

_CODE_REF_RE = re.compile(r"^(code|ref)\s*:\s*(\w+)", re.I)
_memo_code_counts: dict[str, int] = defaultdict(int)


class MetadataAnalyser:
    def __init__(self) -> None:
        # device_id -> set of account numbers seen on that device
        self.device_transaction_map: dict[str, set[str]] = defaultdict(set)

    def analyse_memo(self, description: str, amount: float) -> tuple[float, str]:
        desc = (description or "").strip()
        amount_naira = amount / 100.0

        if len(desc) < 3 and amount_naira > 50000:
            return 0.3, "Very short memo combined with a large amount."

        low = desc.lower()
        if low in ("transfer", "payment", "send", "sent", "cash"):
            return 0.1, "Generic single-word description."

        m = _CODE_REF_RE.match(desc)
        if m:
            code = m.group(2).upper()
            _memo_code_counts[code] += 1
            if _memo_code_counts[code] > 5:
                return 0.4, f"Repeated coded memo pattern (ref/code {code}) seen many times."

        return 0.0, ""

    def analyse_device(self, device_id: str, account_number: str) -> tuple[float, str]:
        if not device_id:
            return 0.0, ""
        holders = self.device_transaction_map[device_id]
        holders.add(account_number)
        n = len(holders)
        if n > 3:
            return 0.5, "Same device_id linked to more than 3 distinct account holders."
        if n == 2:
            return 0.2, "Device shared across two different account holders."
        return 0.0, ""

    def combined_score(
        self, description: str, amount: float, device_id: str, account_number: str
    ) -> tuple[float, str]:
        m_score, m_reason = self.analyse_memo(description, amount)
        d_score, d_reason = self.analyse_device(device_id, account_number)
        if m_score >= d_score:
            score = m_score
            reason = m_reason or d_reason
        else:
            score = d_score
            reason = d_reason or m_reason
        if m_score > 0 and d_score > 0:
            reason = f"{m_reason} {d_reason}".strip()
        return score, reason


metadata_analyser = MetadataAnalyser()
