"""TF-IDF retrieval over Titan FAQ dataset (titan_qa.jsonl)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_KB = _DATA_DIR / "titan_qa.jsonl"
_SAMPLE_KB = _DATA_DIR / "titan_qa.sample.jsonl"
_FALLBACK_SCORE_THRESHOLD = 0.45

_index: dict | None = None


def _resolve_kb_path() -> Path:
    raw = (os.getenv("AGENT_KB_PATH") or "").strip()
    if raw:
        return Path(raw)
    if _DEFAULT_KB.is_file():
        return _DEFAULT_KB
    return _SAMPLE_KB


def _load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _corpus_text(rec: dict) -> str:
    kw = " ".join(rec.get("keywords") or [])
    return f"{rec.get('question', '')} {kw} {rec.get('category', '')}".strip()


def _build_index() -> dict:
    path = _resolve_kb_path()
    if not path.is_file():
        logger.warning("Knowledge base not found at %s", path)
        return {
            "records": [],
            "vectorizer": None,
            "matrix": None,
            "path": str(path),
        }

    records = _load_records(path)
    if not records:
        return {"records": [], "vectorizer": None, "matrix": None, "path": str(path)}

    texts = [_corpus_text(r) for r in records]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    logger.info("Loaded %s FAQ records from %s", len(records), path)
    return {
        "records": records,
        "vectorizer": vectorizer,
        "matrix": matrix,
        "path": str(path),
    }


def _get_index() -> dict:
    global _index
    if _index is None:
        _index = _build_index()
    return _index


def reload_knowledge_base() -> None:
    """Clear cached index (for tests)."""
    global _index
    _index = None


def default_top_k() -> int:
    try:
        return max(1, min(20, int(os.getenv("AGENT_KB_TOP_K", "5"))))
    except ValueError:
        return 5


def retrieve(message: str, k: int | None = None) -> list[dict]:
    """
    Return up to k FAQ records sorted by similarity score (highest first).
    Each item includes: id, category, question, answer, keywords, actions, score.
    """
    idx = _get_index()
    records = idx["records"]
    vectorizer = idx["vectorizer"]
    matrix = idx["matrix"]
    if not records or vectorizer is None or matrix is None:
        return []

    k = k if k is not None else default_top_k()
    query = (message or "").strip()
    if not query:
        return []

    q_vec = vectorizer.transform([query])
    scores = linear_kernel(q_vec, matrix).flatten()
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]

    out: list[dict] = []
    for i, score in ranked:
        if score <= 0:
            continue
        rec = dict(records[i])
        rec["score"] = float(score)
        out.append(rec)
    return out


def best_match(message: str) -> dict | None:
    """Top FAQ hit if any."""
    hits = retrieve(message, k=1)
    return hits[0] if hits else None


def fallback_score_threshold() -> float:
    try:
        return float(os.getenv("AGENT_KB_FALLBACK_THRESHOLD", str(_FALLBACK_SCORE_THRESHOLD)))
    except ValueError:
        return _FALLBACK_SCORE_THRESHOLD


def format_for_prompt(hits: list[dict]) -> str:
    """Compact JSON-ish block for Gemini prompt."""
    slim = []
    for h in hits:
        slim.append(
            {
                "category": h.get("category"),
                "question": h.get("question"),
                "answer": h.get("answer"),
                "score": round(h.get("score", 0), 3),
            }
        )
    return json.dumps(slim, ensure_ascii=False)
