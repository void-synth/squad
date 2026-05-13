# Titan

Project root: **`C:\Users\Youngestage\squad-sentinel`** (open this folder in Cursor or your terminal).

Fraud detection demo platform: FastAPI + PostgreSQL + Redis + Socket.IO backend, and a Vite + React real-time dashboard.

## Prerequisites

- Python 3.11 or newer (tested on 3.13)
- Node.js 18 or newer
- PostgreSQL listening on `localhost:5432` (optional if you set `DATABASE_URL` to SQLite for local smoke tests)
- Redis listening on `localhost:6379`
- A Squad developer account at [https://squadco.com](https://squadco.com) with **sandbox** API keys

## Setup

1. **Backend environment**

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows: Copy-Item .env.example .env
```

Edit `backend/.env` and set at least:

- `SQUAD_SECRET_KEY` / `SQUAD_PUBLIC_KEY` (sandbox)
- `DATABASE_URL` (default targets `squad_sentinel` on Postgres)
- `REDIS_URL`
- `APP_SECRET` (any long random string)

2. **Create the database (Postgres)**

```sql
CREATE DATABASE squad_sentinel;
```

3. **Frontend**

```bash
cd frontend
npm install
```

The file `frontend/.env` contains `VITE_API_URL` and `VITE_SOCKET_URL` pointing at `http://localhost:8000`.

## Running the demo

1. Start **PostgreSQL** and **Redis**.
2. Start the backend (pick one):

```bash
cd backend
bash start.sh
```

Windows PowerShell:

```powershell
cd backend
.\start.ps1
```

3. Start the frontend:

```bash
cd frontend
npm run dev
```

4. Open the dashboard: [http://localhost:5173](http://localhost:5173)

5. In another terminal, run the simulator (uses the same `SQUAD_SECRET_KEY` as the backend for HMAC signing):

```bash
cd backend
python simulate.py
```

Watch the dashboard: transactions stream in, stats update, and high-severity alerts appear for held cases.

## Demo script (cheat sheet)

- Squad sends signed webhooks into our receiver; we verify HMAC, persist `pending`, and enqueue work.
- A background worker scores each payment with three signals: velocity (IsolationForest), money-hop graph centrality, and memo/device metadata.
- High scores flip status to `held` / `flagged`, write `FraudAlert` rows, and push Socket.IO events to the command center.
- The UI shows live throughput, a SOC-style alert card, and a money-hop graph for the sender’s neighbourhood.
- Releasing or escalating an alert hits REST endpoints, updates the database, and rebroadcasts over Socket.IO.

## Common errors

1. **`ModuleNotFoundError` when starting the backend** — activate the virtual environment and run `pip install -r requirements.txt` again from `backend/`.

2. **`DATABASE_URL` / connection refused** — Postgres is not running, the database `squad_sentinel` does not exist, or credentials in `.env` are wrong. If you omit `DATABASE_URL`, the app falls back to a local SQLite file for quick smoke tests only.

3. **Redis / queue errors** — ensure Redis is up on port 6379. The worker silently logs Redis failures; check the backend logs.

4. **Webhook returns 401 Invalid signature** — `SQUAD_SECRET_KEY` in `backend/.env` must match the secret used by `simulate.py` (same variable name). The simulator signs the exact JSON bytes posted to the webhook.

5. **Socket.IO shows disconnected in the UI** — confirm the backend is started with `uvicorn main:app` (the combined ASGI app), that `VITE_SOCKET_URL` matches the backend origin, and that no corporate proxy blocks WebSockets.

## Project layout

- `backend/` — FastAPI app (`main.py`), AI modules under `app/ai/`, services, REST routes, `simulate.py`
- `frontend/` — Vite React dashboard (`src/components`, `src/context`, `src/services`)

## Licence

Hackathon / demo project — adjust before production use.
