"""
Demo simulation: POST signed webhooks to the local backend.

Run from repo: `cd backend && python simulate.py`
Requires backend on :8000, Redis, Postgres, and matching SQUAD_SECRET_KEY in .env.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import random
import secrets
import string
import time
from typing import Any

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

WEBHOOK_URL = os.getenv("SIM_WEBHOOK_URL", "http://localhost:8000/api/v1/webhook/squad")
STATS_URL = os.getenv("SIM_STATS_URL", "http://localhost:8000/api/v1/stats")
SECRET = os.getenv("SQUAD_SECRET_KEY", "your_squad_secret_key_here")


def _sign(body: bytes) -> str:
    return hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


SENDERS: list[dict[str, Any]] = [
    {"name": "Emeka Okafor", "bank": "GTBank", "account": "0123456789", "min_n": 3000, "max_n": 15000},
    {"name": "Ngozi Adeyemi", "bank": "Zenith Bank", "account": "2087654321", "min_n": 5000, "max_n": 20000},
    {"name": "Chidi Nwosu", "bank": "First Bank", "account": "3012345678", "min_n": 2000, "max_n": 12000},
    {"name": "Amina Bello", "bank": "UBA", "account": "1029384756", "min_n": 4000, "max_n": 18000},
    {"name": "Tunde Bakare", "bank": "Access Bank", "account": "0765432109", "min_n": 6000, "max_n": 25000},
    {"name": "Ifeoma Eze", "bank": "GTBank", "account": "0456123789", "min_n": 3500, "max_n": 14000},
    {"name": "Yusuf Garba", "bank": "Zenith Bank", "account": "2233445566", "min_n": 8000, "max_n": 30000},
    {"name": "Chioma Okonkwo", "bank": "First Bank", "account": "3344556677", "min_n": 2500, "max_n": 11000},
    {"name": "Segun Adebayo", "bank": "UBA", "account": "4455667788", "min_n": 7000, "max_n": 22000},
    {"name": "Funke Oladipo", "bank": "Access Bank", "account": "5566778899", "min_n": 4500, "max_n": 16000},
    {"name": "Obinna Ibe", "bank": "GTBank", "account": "6677889900", "min_n": 5000, "max_n": 19000},
    {"name": "Halima Musa", "bank": "Zenith Bank", "account": "7788990011", "min_n": 9000, "max_n": 28000},
    {"name": "Kelechi Ude", "bank": "First Bank", "account": "8899001122", "min_n": 3200, "max_n": 13000},
    {"name": "Bisi Ogunleye", "bank": "UBA", "account": "9900112233", "min_n": 5500, "max_n": 21000},
    {"name": "Dayo Akinola", "bank": "Access Bank", "account": "0011223344", "min_n": 6500, "max_n": 24000},
    {"name": "Nneka Obi", "bank": "GTBank", "account": "1122334455", "min_n": 2800, "max_n": 10000},
    {"name": "Ibrahim Sule", "bank": "Zenith Bank", "account": "2233445560", "min_n": 7500, "max_n": 26000},
    {"name": "Efe Omorogbe", "bank": "First Bank", "account": "3344556601", "min_n": 4000, "max_n": 17000},
    {"name": "Adaeze Nnamdi", "bank": "UBA", "account": "4455667712", "min_n": 4800, "max_n": 15500},
    {"name": "Gbenga Falade", "bank": "Access Bank", "account": "5566778823", "min_n": 5200, "max_n": 20000},
]

RECEIVERS: list[dict[str, Any]] = [
    {"bank": "OPay", "account": "9031112223"},
    {"bank": "OPay", "account": "9042223334"},
    {"bank": "PalmPay", "account": "8053334445"},
    {"bank": "PalmPay", "account": "8064445556"},
    {"bank": "Kuda", "account": "2001555666"},
    {"bank": "Kuda", "account": "2001666777"},
    {"bank": "GTBank", "account": "0111222333"},
    {"bank": "Zenith Bank", "account": "2099887766"},
    {"bank": "First Bank", "account": "3022113344"},
    {"bank": "UBA", "account": "1011223344"},
    {"bank": "Access Bank", "account": "0700112233"},
    {"bank": "OPay", "account": "9077778888"},
    {"bank": "PalmPay", "account": "8089990000"},
    {"bank": "Kuda", "account": "2001777888"},
    {"bank": "UBA", "account": "1022334455"},
]

MEMOS = [
    "school fees",
    "house rent",
    "family support",
    "market purchase",
    "sunday offering",
    "transport fare",
    "utility bill",
]


def _ref() -> str:
    return "sqd_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


def generate_normal_transaction() -> dict[str, Any]:
    s = random.choice(SENDERS)
    r = random.choice(RECEIVERS)
    naira = random.uniform(s["min_n"], s["max_n"])
    kobo = int(round(naira * 100))
    return {
        "transaction_ref": _ref(),
        "amount": float(kobo),
        "sender_account": s["account"],
        "receiver_account": r["account"],
        "sender_bank": s["bank"],
        "receiver_bank": r["bank"],
        "description": random.choice(MEMOS),
        "device_id": f"DEV_{secrets.token_hex(3)}",
        "bvn": f"22{random.randint(10**8, 10**9-1)}",
        "receiver_is_new": False,
    }


def generate_fraud_transaction(fraud_type: str) -> dict[str, Any]:
    if fraud_type == "smurfing":
        s = SENDERS[0]
        r = random.choice([x for x in RECEIVERS if x["bank"] == "OPay"])
        return {
            "transaction_ref": _ref(),
            "amount": float(12_500_000),  # 125,000 NGN in kobo
            "sender_account": s["account"],
            "receiver_account": r["account"],
            "sender_bank": s["bank"],
            "receiver_bank": r["bank"],
            "description": "payment",
            "device_id": "DEVICE_SMURF",
            "bvn": "22123456789",
            "receiver_is_new": True,
        }
    if fraud_type == "velocity_spike":
        s = SENDERS[2]  # Chidi — normal max 12k
        r = random.choice(RECEIVERS)
        return {
            "transaction_ref": _ref(),
            "amount": float(200_000_000),  # 2,000,000 NGN
            "sender_account": s["account"],
            "receiver_account": r["account"],
            "sender_bank": s["bank"],
            "receiver_bank": r["bank"],
            "description": "transfer",
            "device_id": "DEVICE_SPIKE",
            "bvn": "22999888776",
            "receiver_is_new": False,
        }
    if fraud_type == "device_sharing":
        names = ["Emeka Okafor", "Ngozi Adeyemi", "Chidi Nwosu", "Amina Bello", "Tunde Bakare"]
        s = random.choice(SENDERS)
        r = random.choice(RECEIVERS)
        return {
            "transaction_ref": _ref(),
            "amount": float(random.randint(50_000, 500_000)),
            "sender_account": s["account"],
            "receiver_account": r["account"],
            "sender_bank": s["bank"],
            "receiver_bank": r["bank"],
            "description": "cash",
            "device_id": "DEVICE_009",
            "bvn": f"22{random.randint(10**8, 10**9-1)}",
            "receiver_is_new": False,
            "_note": names,
        }
    if fraud_type == "new_bvns":
        s = random.choice(SENDERS)
        r = random.choice(RECEIVERS)
        return {
            "transaction_ref": _ref(),
            "amount": float(5_000_000),
            "sender_account": s["account"],
            "receiver_account": r["account"],
            "sender_bank": s["bank"],
            "receiver_bank": r["bank"],
            "description": "ref: ABC123",
            "device_id": f"DEV_{secrets.token_hex(2)}",
            "bvn": "22111111111",
            "receiver_is_new": True,
        }
    return generate_normal_transaction()


async def _fetch_flagged(client: httpx.AsyncClient) -> int:
    try:
        r = await client.get(STATS_URL, timeout=5.0)
        r.raise_for_status()
        data = r.json()
        return int(data.get("total_flagged", 0))
    except Exception:
        return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="POST signed Squad webhooks to the local backend.")
    p.add_argument(
        "-n",
        "--count",
        type=int,
        default=200,
        metavar="N",
        help="Number of webhook events to send (default: 200). Each uses a unique transaction_ref.",
    )
    return p.parse_args()


async def run_simulation(n_total: int) -> None:
    random.seed(int(time.time()) % 2**32)
    if n_total < 1:
        raise SystemExit("count must be at least 1")
    n_fraud = int(round(n_total * 0.08))
    flags = ["smurfing", "velocity_spike", "device_sharing", "new_bvns"]
    fraud_seq = []
    for _ in range(n_fraud):
        fraud_seq.append(random.choice(flags))
    kinds = ["fraud"] * n_fraud + ["normal"] * (n_total - n_fraud)
    random.shuffle(kinds)
    fraud_iter = iter(fraud_seq)

    async with httpx.AsyncClient() as client:
        for i in range(n_total):
            if kinds[i] == "normal":
                payload = generate_normal_transaction()
            else:
                payload = generate_fraud_transaction(next(fraud_iter))
            payload.pop("_note", None)

            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers = {"Content-Type": "application/json", "x-squad-signature": _sign(body)}
            r = await client.post(WEBHOOK_URL, content=body, headers=headers, timeout=30.0)
            r.raise_for_status()

            if (i + 1) % 10 == 0 or i == 0:
                flagged = await _fetch_flagged(client)
                print(f"Sent {i + 1}/{n_total} transactions... [{flagged} flagged so far]")

            await asyncio.sleep(0.3)


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(run_simulation(args.count))
