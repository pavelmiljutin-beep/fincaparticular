"""Parcelabot Property Report — Apify Actor.

A thin forwarder: it takes a location, calls the Parcelabot partner report
endpoint (``POST /api/partner/reports``) with a shared API key, and pushes
the returned Markdown report to the Actor's default dataset (and a
key-value record). Apify bills the end user; Parcelabot generates the
report. No scraping, no browser — just a proxy.

Auth: set ``PARCELABOT_API_KEY`` as a secret environment variable on the
Actor (preferred), or pass ``apiKey`` in the input.
"""
from __future__ import annotations

import os

import httpx
from apify import Actor

from transform import build_payload, record_from_response

DEFAULT_BASE_URL = "https://parcelabot.duckdns.org"
REQUEST_TIMEOUT_SECONDS = 120.0


async def _maybe_charge() -> None:
    """Monetization hook — billing-agnostic for now.

    To enable Apify pay-per-event billing later, configure the event in
    the Actor's monetization settings and uncomment the charge call:

        await Actor.charge(event_name="report")
    """
    return None


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}

        base_url = (
            inp.get("baseUrl")
            or os.getenv("PARCELABOT_BASE_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/")
        api_key = inp.get("apiKey") or os.getenv("PARCELABOT_API_KEY")
        if not api_key:
            await Actor.fail(
                status_message=(
                    "Missing Parcelabot API key. Set the PARCELABOT_API_KEY "
                    "environment variable or pass 'apiKey' in the input."
                )
            )
            return

        try:
            payload = build_payload(inp)
        except ValueError as exc:
            await Actor.fail(status_message=str(exc))
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "parcelabot-apify-actor/0.1",
        }
        url = f"{base_url}/api/partner/reports"

        Actor.log.info("Requesting report from %s", url)
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
                resp = await http.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            await Actor.fail(status_message=f"Request to Parcelabot failed: {exc}")
            return

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("message") or resp.text
            except Exception:
                detail = resp.text
            await Actor.fail(
                status_message=(
                    f"Parcelabot returned HTTP {resp.status_code}: {detail}"
                )
            )
            return

        data = resp.json()
        record = record_from_response(data)

        await Actor.push_data(record)
        if record.get("markdown"):
            await Actor.set_value(
                "REPORT.md", record["markdown"], content_type="text/markdown"
            )
        await _maybe_charge()
        Actor.log.info(
            "Report delivered (%s chapters).", record.get("chapterCount")
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
