"""Titan FAQ knowledge base retrieval tests."""

from pathlib import Path

import pytest

from app.ai.agent.knowledge_base import (
    _build_index,
    reload_knowledge_base,
    retrieve,
)

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "app" / "ai" / "agent" / "data" / "titan_qa.sample.jsonl"


@pytest.fixture(autouse=True)
def _use_sample_kb(monkeypatch):
    monkeypatch.setenv("AGENT_KB_PATH", str(SAMPLE_PATH))
    reload_knowledge_base()
    yield
    reload_knowledge_base()


def test_load_sample_records():
    idx = _build_index()
    assert len(idx["records"]) >= 15


def test_retrieve_greeting():
    hits = retrieve("hello", k=3)
    assert hits
    categories = {h["category"] for h in hits}
    assert "greeting" in categories


def test_retrieve_show_flagged():
    hits = retrieve("show flagged transactions", k=3)
    assert hits
    top = hits[0]
    assert top["category"] in ("actions", "dashboard", "paraphrase")
    assert top.get("score", 0) > 0


def test_retrieve_bolu_daniel():
    hits = retrieve("what links bolu and daniel opay", k=2)
    assert hits
    assert any("bolu" in h.get("question", "").lower() or h.get("category") == "demo_entities" for h in hits)


def test_generator_produces_five_thousand():
    import subprocess
    import sys

    backend = Path(__file__).resolve().parents[1]
    script = backend / "scripts" / "generate_titan_qa_dataset.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(backend),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    out = backend / "app" / "ai" / "agent" / "data" / "titan_qa.jsonl"
    assert out.is_file()
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5000
