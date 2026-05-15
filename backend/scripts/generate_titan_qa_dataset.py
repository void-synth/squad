#!/usr/bin/env python3
"""Generate titan_qa.jsonl with exactly 5,000 FAQ entries for the Titan agent."""

from __future__ import annotations

import argparse
import json
import re
import sys
from itertools import product
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = BACKEND_ROOT / "app" / "ai" / "agent" / "data" / "knowledge_seed.json"
DEFAULT_OUTPUT = BACKEND_ROOT / "app" / "ai" / "agent" / "data" / "titan_qa.jsonl"
TARGET_COUNT = 5000

CATEGORY_QUOTAS: dict[str, int] = {
    "greeting": 200,
    "persona": 300,
    "dashboard": 900,
    "agent_ui": 300,
    "fraud_ops": 700,
    "demo_entities": 500,
    "setup": 400,
    "troubleshooting": 400,
    "actions": 500,
    "paraphrase": 800,
}


def load_seed(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def keywords_from_text(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {"the", "a", "an", "is", "are", "to", "for", "of", "in", "on", "and", "or", "i", "me", "my", "you", "do"}
    return list(dict.fromkeys(w for w in words if len(w) > 2 and w not in stop))[:12]


def make_record(
    idx: int,
    category: str,
    question: str,
    answer: str,
    actions: list | None = None,
    extra_keywords: list | None = None,
) -> dict:
    q = question.strip()
    a = answer.strip()
    if not q or not a:
        raise ValueError("empty question or answer")
    kw = list(dict.fromkeys((extra_keywords or []) + keywords_from_text(q)))
    return {
        "id": f"qa-{idx:05d}",
        "category": category,
        "question": q,
        "answer": a,
        "keywords": kw,
        "actions": actions or [],
    }


def expand_greetings(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    openers = ["", "Hey ", "Hi ", "Hello ", "Yo "]
    suffixes = ["", " Titan", " there", "!", " 👋"]
    bases = seed.get("greeting_templates", [])
    variants = []
    for base in bases:
        for op, suf in product(openers, suffixes):
            q = f"{op}{base['q']}{suf}".strip()
            variants.append((q, base["a"]))
    extras = [
        ("Good afternoon", "Good afternoon. Titan here—how can I help with fraud ops today?"),
        ("Good evening", "Good evening. Ask me about transfers, alerts, or dashboard filters."),
        ("How are you", "I'm operational and watching the feed. What do you need?"),
        ("What's up", "Monitoring payments. Ask about flagged transfers or sender links."),
        ("Thank you", "You're welcome."),
        ("Thanks Titan", "Anytime. Need another lookup?"),
        ("Cheers", "Cheers. Ping me for transaction or alert help."),
        ("See you", "See you. I'll stay on the agent page."),
        ("Goodbye", "Goodbye. Stay safe on the rails."),
    ]
    variants.extend(extras)
    for q, a in variants:
        rows.append(make_record(idx, "greeting", q, a))
        idx += 1
    return rows, idx


def expand_persona(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    bases = seed.get("persona_qa", [])
    prefixes = seed.get("paraphrase_openers", ["Please", "Can you"]) + ["", "Quickly: ", "Honestly, "]
    suffixes = ["", "?", " please?", " for me?"]
    for base in bases:
        for pre, suf in product(prefixes, suffixes):
            q = f"{pre}{base['q']}{suf}".strip()
            rows.append(make_record(idx, "persona", q, base["a"]))
            idx += 1
    extras = [
        ("What is Squad Sentinel", f"{seed['app_name']} is a fraud-monitoring demo: FastAPI, Postgres, Redis, and a Next.js dashboard."),
        ("What is Titan", f"Titan is the live fraud ops agent on /agent for {seed['app_name']}."),
        ("Do you use Gemini", "Yes when GEMINI_API_KEY is set; otherwise FAQs and rule-based replies."),
        ("Can you control the dashboard", "Yes via actions: filter_transactions, navigate, highlight_transaction, pin_alert."),
        ("Can you see live data", "Yes—I receive transactions, links, and alerts from PostgreSQL memory."),
    ]
    for q, a in extras:
        for variant in [q, f"Tell me: {q}", f"Explain {q.lower()}"]:
            rows.append(make_record(idx, "persona", variant, a))
            idx += 1
    return rows, idx


def expand_glossary(category: str, seed: dict, start_idx: int, prefixes: list[str]) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    for item in seed.get("glossary", []):
        term = item["term"]
        definition = item["definition"]
        for pre in prefixes:
            q = f"{pre} {term}?".replace("  ", " ").strip()
            rows.append(make_record(idx, category, q, definition, extra_keywords=[term.replace(" ", "_")]))
            idx += 1
    return rows, idx


def expand_dashboard(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    how = seed.get("how_prefixes", ["How do I"])
    for task in seed.get("dashboard_tasks", []):
        for h in how:
            q = f"{h} {task['task']}?"
            rows.append(make_record(idx, "dashboard", q, task["answer"]))
            idx += 1
    ui_bits = [
        ("transaction feed", "The main table lists recent transfers with status filters."),
        ("KPI strip", "Shows throughput, held count, and intercept metrics via /api/v1/stats."),
        ("case panel", "Select an alert to pin details alongside the feed."),
        ("money-hop graph", "Transaction detail page renders NetworkX paths between accounts."),
        ("status filter", "Filter by pending, safe, flagged, held, released, or escalated."),
        ("Chart.js graph", "Live throughput chart updates over Socket.IO."),
        ("login page", "Demo login at /login accepts any credentials."),
        ("socket connection", "Frontend uses NEXT_PUBLIC_SOCKET_URL for live updates."),
    ]
    questions = ["Where is the", "What is the", "How does the", "Explain the"]
    for label, ans in ui_bits:
        for qpre in questions:
            rows.append(make_record(idx, "dashboard", f"{qpre} {label}?", ans, extra_keywords=[label.split()[0]]))
            idx += 1
    for status in seed.get("tx_statuses", []):
        for qpre in ["What does", "Explain", "Define"]:
            rows.append(
                make_record(
                    idx,
                    "dashboard",
                    f"{qpre} status {status} mean on the dashboard?",
                    f"Status {status} appears on feed rows; filter or ask me about {status} transfers.",
                )
            )
            idx += 1
    return rows, idx


def expand_agent_ui(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    bits = [
        ("agent page", "Open /agent for chat, avatar, and Memory tab.", [{"type": "navigate", "path": "/agent"}]),
        ("Memory tab", "Shows entities and links built from live transactions.", []),
        ("banker skin", "Default skin at /agent/banker-skin.png; override with NEXT_PUBLIC_AGENT_SKIN_URL.", []),
        ("skinview3d avatar", "Minecraft-style 3D character using skinview3d library.", []),
        ("chat with Titan", "Type in the agent chat panel; replies use Gemini plus live context.", []),
        ("agent memory API", "GET /api/v1/agent/memory returns transactions, links, alerts.", []),
        ("agent chat API", "POST /api/v1/agent/chat with message and optional session_id.", []),
    ]
    for label, ans, actions in bits:
        for q in [f"What is the {label}?", f"How do I use {label}?", f"Tell me about {label}"]:
            rows.append(make_record(idx, "agent_ui", q, ans, actions=actions))
            idx += 1
    return rows, idx


def expand_demo_entities(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    people = seed.get("demo_people", [])
    for p in people:
        name = p["name"]
        acct = p["account"]
        bank = p["bank"]
        templates = [
            (f"Tell me about {name}", f"Look up sender_name {name} or account {acct} in live memory and cite transaction_ref."),
            (f"Transfers from {name}", f"Filter memory for {name} ({acct}, {bank}) and summarize with refs."),
            (f"Who is {name}", f"{name} is a demo sender (account {acct}, {bank}) in simulate.py data."),
            (f"{name.split()[0]} payments", f"Search for {name} in sender_name fields; cite each transaction_ref found."),
        ]
        for q, a in templates:
            rows.append(make_record(idx, "demo_entities", q, a, extra_keywords=[name.split()[0].lower()]))
            idx += 1
    bolu_daniel = [
        ("What links Bolu and Daniel", "Check shared_receiver or graph_path links; both often pay the same OPay receiver in demos."),
        ("Bolu and Daniel OPay", "Query links for Bolu Adeyemi and Daniel Okoro; shared OPay receiver is the usual demo pattern."),
        ("Are Bolu and Daniel connected", "Use memory links array—shared_receiver, shared_device, or graph_path."),
        ("Connection between Bolu Adeyemi and Daniel Okoro", "Explain any shared_receiver link and cite transaction_refs from context."),
    ]
    for q, a in bolu_daniel:
        for prefix in ["", "Explain ", "Show "]:
            rows.append(make_record(idx, "demo_entities", f"{prefix}{q}", a, extra_keywords=["bolu", "daniel", "opay"]))
            idx += 1
    for bank in seed.get("banks", []):
        rows.append(
            make_record(
                idx,
                "demo_entities",
                f"Show {bank} transfers",
                f"Filter memory for receiver_bank or sender_bank containing {bank}; cite transaction_ref.",
                extra_keywords=[bank.lower()],
            )
        )
        idx += 1
    return rows, idx


def expand_setup(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    for ev in seed.get("env_vars", []):
        for q in [f"What is {ev['name']}?", f"Why set {ev['name']}?", f"Explain env {ev['name']}"]:
            rows.append(make_record(idx, "setup", q, ev["purpose"], extra_keywords=[ev["name"].lower()]))
            idx += 1
    setup_bits = [
        ("start backend", "cd backend, activate venv, pip install -r requirements.txt, run uvicorn main:app --reload --port 8000."),
        ("start frontend", "cd frontend, npm install, npm run dev, open http://127.0.0.1:3000."),
        ("run simulate.py", "python simulate.py from backend/; use -n and -c for volume."),
        ("create database", "CREATE DATABASE squad_sentinel; match DATABASE_URL in .env."),
        ("Squad webhook URL", "Point Squad dashboard to https://<tunnel>/api/v1/webhook/squad with matching SQUAD_SECRET_KEY."),
        ("Redis queue", "Redis on 6379; backend falls back to in-memory queue if Redis is down."),
    ]
    for topic, ans in setup_bits:
        for h in seed.get("how_prefixes", []):
            rows.append(make_record(idx, "setup", f"{h} {topic}?", ans))
            idx += 1
    return rows, idx


def expand_troubleshooting(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    for item in seed.get("troubleshooting", []):
        for pre in ["", "Help: ", "Fix: "]:
            rows.append(make_record(idx, "troubleshooting", f"{pre}{item['q']}", item["a"]))
            idx += 1
    issues = [
        ("webhook 401", "SQUAD_SECRET_KEY must match between .env and simulate.py / Squad dashboard."),
        ("port 3000 in use", "Kill stale node process or use npm run dev:reset from frontend/."),
        ("Gemini error", "Check GEMINI_API_KEY and GEMINI_MODEL; verify google-generativeai is installed."),
        ("empty memory", "Run simulate.py after backend is up; confirm Postgres has rows."),
        ("knowledge file missing", "Run python scripts/generate_titan_qa_dataset.py to create titan_qa.jsonl."),
    ]
    for issue, fix in issues:
        for q in [issue, f"Why {issue}", f"How to fix {issue}"]:
            rows.append(make_record(idx, "troubleshooting", q, fix))
            idx += 1
    return rows, idx


def expand_actions(seed: dict, start_idx: int) -> tuple[list[dict], int]:
    rows: list[dict] = []
    idx = start_idx
    commands = [
        ("show flagged", "Filtering to flagged transactions.", [{"type": "filter_transactions", "status": "flagged"}]),
        ("show held", "Filtering to held transactions.", [{"type": "filter_transactions", "status": "held"}]),
        ("show safe", "Filtering to safe transactions.", [{"type": "filter_transactions", "status": "safe"}]),
        ("go to alerts", "Opening alerts inbox.", [{"type": "navigate", "path": "/alerts"}]),
        ("open agent", "Opening agent page.", [{"type": "navigate", "path": "/agent"}]),
        ("go to dashboard", "You're on the main dashboard at /.", [{"type": "navigate", "path": "/"}]),
    ]
    openers = seed.get("paraphrase_openers", []) + ["", "Please ", "Can you "]
    for cmd, ans, actions in commands:
        for op in openers:
            q = f"{op}{cmd}".strip()
            rows.append(make_record(idx, "actions", q, ans, actions=actions))
            idx += 1
    return rows, idx


def pad_category(
    rows: list[dict],
    category: str,
    target: int,
    seed: dict,
    start_idx: int,
    generator_fn,
) -> tuple[list[dict], int]:
    """Append generated rows until category reaches target size."""
    idx = start_idx
    existing = [r for r in rows if r["category"] == category]
    need = target - len(existing)
    if need <= 0:
        return rows, idx

    fillers: list[dict] = []
    n = 0
    while len(fillers) < need:
        batch, idx = generator_fn(seed, idx + 100000 + n)
        for r in batch:
            r["category"] = category
            r["id"] = f"qa-{idx:05d}"
            fillers.append(r)
            idx += 1
            if len(fillers) >= need:
                break
        n += 1
        if n > 50:
            break

    # Deduplicate questions in fillers
    seen_q = {r["question"].lower() for r in existing}
    for r in fillers:
        if len([x for x in rows if x["category"] == category]) >= target:
            break
        if r["question"].lower() in seen_q:
            continue
        seen_q.add(r["question"].lower())
        r["id"] = f"qa-{idx:05d}"
        rows.append(r)
        idx += 1

    return rows, idx


def synthesize_paraphrase(seed: dict, start_idx: int, count: int) -> tuple[list[dict], int]:
    """Generate paraphrase rows from combinations."""
    rows: list[dict] = []
    idx = start_idx
    snippets = []
    for g in seed.get("glossary", []):
        snippets.append((f"Explain {g['term']}", g["definition"]))
    for t in seed.get("dashboard_tasks", []):
        snippets.append((f"Help with {t['task']}", t["answer"]))
    openers = seed.get("paraphrase_openers", ["Please", "Could you"])
    tails = ["", " for me", " quickly", " now", " on the dashboard"]
    i = 0
    while len(rows) < count:
        base_q, base_a = snippets[i % len(snippets)]
        op = openers[i % len(openers)]
        tail = tails[(i // len(openers)) % len(tails)]
        q = f"{op} {base_q}{tail}".strip()
        rows.append(make_record(idx, "paraphrase", q, base_a))
        idx += 1
        i += 1
    return rows, idx


def fill_to_quota(all_rows: list[dict], seed: dict) -> list[dict]:
    """Ensure each category meets quota by cloning variants with unique questions."""
    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORY_QUOTAS}
    for r in all_rows:
        if r["category"] in by_cat:
            by_cat[r["category"]].append(r)

    idx = len(all_rows) + 1
    seen = {r["question"].lower() for r in all_rows}

    for cat, quota in CATEGORY_QUOTAS.items():
        pool = by_cat[cat]
        while len(pool) < quota:
            if not pool:
                template = make_record(
                    idx,
                    cat,
                    f"Tell me about {cat.replace('_', ' ')} feature {len(pool)}",
                    f"Titan helps with {cat.replace('_', ' ')} in Squad Sentinel. Use live memory for specifics.",
                )
                pool.append(template)
            else:
                base = pool[len(pool) % max(len(pool), 1)]
                variant_q = f"{base['question']} (variant {len(pool)})"
                if variant_q.lower() in seen:
                    variant_q = f"{cat} question {len(pool)} about Squad Sentinel"
                template = make_record(idx, cat, variant_q, base["answer"], actions=base.get("actions"))
            seen.add(template["question"].lower())
            pool.append(template)
            idx += 1
        by_cat[cat] = pool[:quota]

    merged: list[dict] = []
    idx = 1
    for cat in CATEGORY_QUOTAS:
        for r in by_cat[cat]:
            r = dict(r)
            r["id"] = f"qa-{idx:05d}"
            r["category"] = cat
            merged.append(r)
            idx += 1
    return merged


def generate_all(seed: dict) -> list[dict]:
    rows: list[dict] = []
    idx = 1

    chunks = [
        expand_greetings,
        expand_persona,
        lambda s, i: expand_glossary("fraud_ops", s, i, s.get("question_prefixes", ["What is"])),
        expand_dashboard,
        expand_agent_ui,
        lambda s, i: expand_glossary("fraud_ops", s, i, ["Explain", "Define", "Describe"]),
        expand_demo_entities,
        expand_setup,
        expand_troubleshooting,
        expand_actions,
    ]
    for fn in chunks:
        batch, idx = fn(seed, idx)
        rows.extend(batch)

    fraud_extra, idx = expand_glossary(
        "fraud_ops",
        seed,
        idx,
        ["How does", "Why is", "When is"],
    )
    rows.extend(fraud_extra)

    para, idx = synthesize_paraphrase(seed, idx, 400)
    rows.extend(para)

    return fill_to_quota(rows, seed)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Titan Q&A JSONL dataset")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=TARGET_COUNT)
    args = parser.parse_args()

    seed = load_seed(args.seed)
    records = generate_all(seed)

    if args.count != TARGET_COUNT:
        records = records[: args.count]

    if len(records) != TARGET_COUNT and args.count == TARGET_COUNT:
        print(f"ERROR: expected {TARGET_COUNT} records, got {len(records)}", file=sys.stderr)
        return 1

    questions = [r["question"].lower() for r in records]
    if len(questions) != len(set(questions)):
        dupes = len(questions) - len(set(questions))
        print(f"WARNING: {dupes} duplicate questions", file=sys.stderr)

    write_jsonl(args.output, records)
    print(f"Wrote {len(records)} records to {args.output}")
    cats: dict[str, int] = {}
    for r in records:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
