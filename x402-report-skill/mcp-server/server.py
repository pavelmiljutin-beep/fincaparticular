"""Parcelabot x402 report MCP server.

Exposes two tools for AI agents:

* ``check_report_coverage(lat, lng, radius_km?)`` — FREE. How many real POIs +
  which report chapters exist near a coordinate, so the agent decides whether to
  order.
* ``order_full_report(lat, lng, language?)`` — PAID via x402 (TON/USDT). Orders
  a full parcel-level report, waits for it, and returns the Markdown.

Run:
    pip install -r requirements.txt
    python server.py

Environment:
    PARCELABOT_BASE_URL   API base (default https://parcelabot.duckdns.org)
    EVM_PRIVATE_KEY       EVM wallet private key used to pay (required to order)
"""
from __future__ import annotations

import asyncio
import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get(
    "PARCELABOT_BASE_URL", "https://parcelabot.duckdns.org"
).rstrip("/")
USER_AGENT = "parcelabot-x402-mcp/1.0"
POLL_TIMEOUT_SECONDS = 300

mcp = FastMCP("parcelabot-x402-report")


@mcp.tool()
async def check_report_coverage(
    lat: float, lng: float, radius_km: float | None = None
) -> str:
    """Return honest nearby-POI counts + report chapters for a coordinate (FREE).

    Use this BEFORE ordering. If ``coverage_level`` is ``none`` or ``sparse``,
    the data is thin — confirm with the user before paying. No payment is made.
    """
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
        return json.dumps(resp.json(), ensure_ascii=False)


def _build_x402_client():
    from eth_account import Account
    from x402 import x402Client
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact.register import register_exact_evm_client

    key = os.environ.get("EVM_PRIVATE_KEY")
    if not key:
        raise RuntimeError("EVM_PRIVATE_KEY is required to pay for a report.")
    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(key)))
    return client


@mcp.tool()
async def order_full_report(
    lat: float, lng: float, language: str = "en"
) -> str:
    """Order + pay for a full parcel-level report at a coordinate (PAID via x402).

    Pays in USDT on TON, waits for the report, and returns its Markdown. Call
    ``check_report_coverage`` first. Supported languages: en, es, ru, fr, uk,
    de, ar. Raises on unserviceable locations or wallet/payment errors.
    """
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
            return f"Location not serviceable: {resp.text}"
        resp.raise_for_status()
        job = resp.json()

    job_id = job["job_id"]
    interval = int(job.get("poll_after_seconds", 5))
    waited = 0
    async with httpx.AsyncClient(timeout=30) as http:
        while waited < POLL_TIMEOUT_SECONDS:
            poll = await http.get(
                f"{BASE_URL}/api/agent/reports/{job_id}",
                headers={"User-Agent": USER_AGENT},
            )
            poll.raise_for_status()
            data = poll.json()
            status = data.get("status")
            if status == "ready":
                return data.get("markdown", "(no markdown returned)")
            if status == "failed":
                return f"Report failed: {data.get('error')}"
            await asyncio.sleep(interval)
            waited += interval
    return "Timed out waiting for the report."


if __name__ == "__main__":
    mcp.run()
