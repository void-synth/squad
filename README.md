#Squad Sentinel (Titan)

Fraud-monitoring demo: **FastAPI** + **PostgreSQL** + **Redis** + **Socket.IO** backend, and a **Next.js** real-time operations UI (HeroUI, Chart.js, live feed, alert queue).

> **Repository layout:** This README assumes the git root is the folder that contains **`backend/`** and **`frontend/`** side by side. When you push to GitHub, those directories should appear at the **top level** of the repo—not nested inside another folder.

## Prerequisites

- **Python** 3.11+ (3.13 works)
- **Node.js** 18+
- **PostgreSQL** on `localhost:5432` (or set `DATABASE_URL` in `.env`)
- **Redis** on `localhost:6379`
- **Squad** sandbox API keys from [squadco.com](https://squadco.com)

## Quick start

### 1. Backend

```bash
cd backend
python -m venv venv


Activate the venv:

Windows (PowerShell): .\venv\Scripts\Activate.ps1
macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
Copy env template and edit:

Windows: Copy-Item .env.example .env
macOS / Linux: cp .env.example .env
Set at least: `SQUAD_SECRET_KEY`, `SQUAD_PUBLIC_KEY`, `DATABASE_URL`, `REDIS_URL`, `APP_SECRET` (see [backend/.env.example](backend/.env.example)). Optional flags there control legacy webhook signatures, ingest-time Squad verify, and payout calls.

#### Squad dashboard webhooks (real sandbox)

- **Webhook URL** in the Squad dashboard: `https://<your-public-host>/api/v1/webhook/squad`. Your laptop is not reachable from the internet; use **ngrok**, **Cloudflare Tunnel**, or another HTTPS tunnel to your local `:8000`.
- **`SQUAD_SECRET_KEY`** in `backend/.env` must match the secret key used in the Squad dashboard so signatures verify.
- Official Squad posts **`x-squad-encrypted-body`**: HMAC-**SHA512** of the **raw** JSON body (hex, case-insensitive). Local [`simulate.py`](backend/simulate.py) uses **`x-squad-signature`**: HMAC-**SHA256** (legacy). Keep **`SQUAD_WEBHOOK_LEGACY_SHA256=true`** while using `simulate.py`; set to **`false`** for stricter production-like behaviour.
- **Never commit** live keys to git; keep them in `backend/.env` only. Rotate keys if they were ever exposed.

Create the database if needed:

CREATE DATABASE squad_sentinel;
2. Frontend
cd frontend
npm install
frontend/.env should point the UI at the API (defaults are fine for local dev):

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SOCKET_URL=http://localhost:8000
3. Run
Start PostgreSQL and Redis.

Backend (from backend/):

bash start.sh
Windows:

.\start.ps1
Or manually: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

Frontend (from frontend/):

npm run dev
Open **http://127.0.0.1:3000** (Next.js dev server; the terminal prints the exact URL). You will be sent to **`/login`** first: demo auth accepts **any email and password** (stored only in the browser).

If you see **404** on port **5173**, an old process (often a pre-migration Vite server) may still be bound there. Stop it (Task Manager / `taskkill` on Windows, or close the terminal that started it), or run **`npm run dev:5173`** only after that port is free.

4. Simulator (optional)

In another terminal, from `backend/` (venv active, same `SQUAD_SECRET_KEY` as the server):

```bash
python simulate.py
```

You should see transactions stream in, stats update, and alerts for held / escalated cases.

**High-volume load (same real path: webhook → DB → Redis → risk engine).** Use concurrency to POST many signed webhooks in parallel; the worker scores each one (velocity / graph / metadata).

```bash
python simulate.py -n 800 -c 40
python simulate.py -n 2000 -c 50 --fraud-rate 0.12
python simulate.py -n 200 -c 1
```

| Flag | Purpose |
|------|---------|
| `-n` / `--count` | Number of unique `transaction_ref` events (default `200`) |
| `-c` / `--concurrency` | Max in-flight HTTP posts (default `1`; try `20`–`80` to stress the stack) |
| `--fraud-rate` | Share of fraud-style payloads (default `0.08`) |
| `--delay` | With `-c 1`, pause after each post (default `0.3` s); with `-c` greater than `1`, default is no delay |
| `--progress-every` | Print progress every *M* completions (default `50`) |
| `--seed` | Optional RNG seed for repeatable runs |

Optional env in `backend/.env`: `SIM_WEBHOOK_URL`, `SIM_STATS_URL` if the API is not on `localhost:8000`.

What it demonstrates
Webhooks: Signed Squad-style payloads are verified (HMAC), stored as pending, and queued.
Worker: Background processing scores payments (velocity / graph / metadata style signals).
Outcomes: High scores move transactions to held / flagged, create FraudAlert rows, and emit Socket.IO updates.
UI: Live throughput (Chart.js), KPI strip, transaction feed with filters, alert / case panel, transaction detail with money-hop graph, alerts inbox.
Live agent: Open `/agent` for a Minecraft-style banker character ([skinview3d](https://github.com/bs-community/skinview3d) + `frontend/public/agent/banker-skin.png`), Memory tab (transaction links by name/account), and Gemini-powered Q&A. Set `GEMINI_API_KEY` in `backend/.env`; optional `NEXT_PUBLIC_AGENT_SKIN_URL` in `frontend/.env` to swap the 64×64 skin PNG (demo skin only—replace for production). Example: *What links Bolu and Daniel's OPay transfers?*

**Titan FAQ knowledge base (5,000 Q&A pairs):** After clone, generate the dataset once from `backend/`:

```bash
python scripts/generate_titan_qa_dataset.py
```

This writes `backend/app/ai/agent/data/titan_qa.jsonl` (greetings, dashboard help, fraud ops, setup, demo entities). At chat time, Titan retrieves similar FAQs (TF-IDF) and sends them to Gemini together with live transaction memory. Without `GEMINI_API_KEY`, strong FAQ matches still answer from the file. Optional env: `AGENT_KB_PATH`, `AGENT_KB_TOP_K` (default `5`), `AGENT_KB_FALLBACK_THRESHOLD` (default `0.45`). Tests use `titan_qa.sample.jsonl` when the full file is absent.
Project layout
Path	Role
backend/main.py
ASGI entry (FastAPI + Socket.IO)
backend/app/api/
REST routes (transactions, webhooks)
backend/app/ai/
Risk / graph / NLP style modules
backend/app/services/
Processor, Squad client, stats
backend/simulate.py
Local transaction + webhook simulator
frontend/src/
Next.js app router (`app/`), views, dashboard, context, services
Troubleshooting
Issue	What to check
ModuleNotFoundError (backend)
Venv activated; pip install -r requirements.txt from backend/.
Database connection errors
Postgres running; database exists; DATABASE_URL in .env.
Redis / queue issues
Redis on port 6379; backend logs.
Webhook 401 / invalid signature
SQUAD_SECRET_KEY in backend/.env must match the key used by simulate.py.
UI shows offline / no live data
Backend on port 8000; NEXT_PUBLIC_API_URL / NEXT_PUBLIC_SOCKET_URL match; WebSockets not blocked.
UI build / cache issues
Stop the dev server, remove `frontend/.next` if needed, then `npm run dev` again. If the browser shows **500** or **Cannot find module './NNN.js'** in dev, run **`npm run dev:reset`** from `frontend/` (clears `.next` then starts Next).
Scripts (frontend)
npm run dev — Next.js dev server (port **3000** by default).
npm run dev:5173 — same dev server on port 5173 if you prefer that port and it is not in use.
npm run build — production build.
npm run dev:reset — delete `.next` then start the dev server (fixes many dev **500** / missing chunk errors).
npm run build:clean — `clean` then `build`.
npm run start — production server (port **3000** by default).
npm run lint — ESLint (Next.js config).
Licence
Hackathon / demo — not production-hardened. Adapt licensing before real deployment.

