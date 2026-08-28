#!/usr/bin/env python3
"""Order a full Parcelabot report as an AI agent, paying with x402 (USDC/EVM).

Flow:
  1. (optional) GET  /api/agent/coverage        — free; how much data is nearby.
  2.            POST /api/agent/reports          — x402 paid; returns a job id.
  3.            GET  /api/agent/reports/{job_id} — poll until Markdown is ready.

Environment:
  PARCELABOT_BASE_URL   API base (default https://parcelabot.duckdns.org)
  EVM_PRIVATE_KEY       EVM wallet private key used to pay (required to order)

Install:
  pip install "x402[httpx]" eth-account

Usage:
  python order_report.py --coverage 40.4168 -3.7038 [--radius-km 5]
  python order_report.py --order    40.4168 -3.7038 [--language en]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

BASE_URL = os.environ.get(
    "PARCELABOT_BASE_URL", "https://parcelabot.duckdns.org"
).rstrip("/")
USER_AGENT = "parcelabot-x402-skill/1.0"
POLL_TIMEOUT_SECONDS = 300


async def check_coverage(
    lat: float, lng: float, radius_km: float | None = None
) -> dict:
    """Free coverage preview — no payment."""
    import httpx

    params: dict[str, object] = {"lat": lat, "lng": lng}
    if radius_km:
        params["radius_km"] = radius_km
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.get(
            f"{BASE_URL}/api/agent/coverage",
            params=params,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        return resp.json()


def _build_x402_client():
    """Create an x402 client that can sign EVM (USDT) payments."""
    from eth_account import Account
    from x402 import x402Client
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact.register import register_exact_evm_client

    key = os.environ.get("EVM_PRIVATE_KEY")
    if not key:
        raise SystemExit("EVM_PRIVATE_KEY is required to pay for a report.")
    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(key)))
    return client


async def order(lat: float, lng: float, language: str = "en") -> tuple[str, int]:
    """Pay via x402 and enqueue a report; returns (job_id, poll_interval)."""
    from x402.http.clients import x402HttpxClient

    client = _build_x402_client()
    payload = {"lat": lat, "lng": lng, "language": language}
    async with x402HttpxClient(client) as http:
        resp = await http.post(
            f"{BASE_URL}/api/agent/reports",
            json=payload,
            headers={"User-Agent": USER_AGENT},
        )
        await resp.aread()
        if resp.status_code == 422:
            raise SystemExit(f"Location not serviceable: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
    return data["job_id"], int(data.get("poll_after_seconds", 5))


async def poll(job_id: str, interval: int) -> dict:
    """Poll a report job until it is ready or fails."""
    import httpx

    waited = 0
    async with httpx.AsyncClient(timeout=30) as http:
        while waited < POLL_TIMEOUT_SECONDS:
            resp = await http.get(
                f"{BASE_URL}/api/agent/reports/{job_id}",
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "ready":
                return data
            if status == "failed":
                raise SystemExit(f"Report failed: {data.get('error')}")
            await asyncio.sleep(interval)
            waited += interval
    raise SystemExit("Timed out waiting for the report.")


async def _run(args: argparse.Namespace) -> None:
    if args.coverage is not None:
        lat, lng = args.coverage
        data = await check_coverage(lat, lng, args.radius_km)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    lat, lng = args.order
    job_id, interval = await order(lat, lng, args.language)
    print(f"# ordered job {job_id}; polling every {interval}s...", flush=True)
    result = await poll(job_id, interval)
    print(result.get("markdown", "(no markdown returned)"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Order a Parcelabot report via x402 (USDC/EVM)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--coverage",
        nargs=2,
        type=float,
        metavar=("LAT", "LNG"),
        help="Free coverage preview for a coordinate (no payment).",
    )
    group.add_argument(
        "--order",
        nargs=2,
        type=float,
        metavar=("LAT", "LNG"),
        help="Order + pay for a full report at a coordinate.",
    )
    parser.add_argument("--radius-km", type=float, default=None)
    parser.add_argument("--language", default="en")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
