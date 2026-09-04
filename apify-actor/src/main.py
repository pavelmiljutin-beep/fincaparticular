"""Parcelabot Property Report — Apify Actor.

A thin forwarder: it takes a location, calls the Parcelabot partner report
endpoint (``POST /api/partner/reports``) with a shared API key, and pushes
the returned structured report to the Actor's default dataset. Apify charges
the ``report-generated`` event only after a full report is delivered.
Parcelabot generates the report. No
scraping, no browser — just a proxy.

Two modes:

* ``dryRun: true`` — a **free** coverage preview (``GET
  /api/partner/coverage``): which chapters exist here, how dense the local
  data is, and how many bytes/tokens each output format would cost. Use it
  to decide whether the full report is worth ordering.
* default — the full report. JSON facts by default; base64 map images are
  off unless ``includeImages`` is set, and even then they are written to
  the key-value store rather than inlined into the dataset record.

Auth: set ``PARCELABOT_API_KEY`` as a secret environment variable on the
Actor (preferred), or pass ``apiKey`` in the input.
"""
from __future__ import annotations

import asyncio
import base64
import os

import httpx
from apify import Actor

from transform import (
    build_payload,
    coverage_params,
    coverage_record,
    quota_record,
    record_from_response,
)

DEFAULT_BASE_URL = "https://parcelabot.duckdns.org"
REQUEST_TIMEOUT_SECONDS = 120.0
COVERAGE_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3.0


def _kvs_record_ref(key: str) -> dict:
    store_id = os.getenv("APIFY_DEFAULT_KEY_VALUE_STORE_ID")
    out = {"keyValueStoreKey": key, "contentType": "image/png"}
    if store_id:
        out["keyValueStoreId"] = store_id
        out["apiUrl"] = (
            f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{key}"
        )
    return out


def _subscriber_headers() -> dict:
    """Identify the Apify user and run to the upstream service."""
    headers = {}
    user_id = os.getenv("APIFY_USER_ID")
    run_id = os.getenv("APIFY_ACTOR_RUN_ID")
    if user_id:
        headers["X-Parcelabot-Subscriber"] = user_id
    if run_id:
        headers["X-Parcelabot-Run"] = run_id
    return headers


async def _store_images(images: list) -> list:
    """Move base64 images out of the record and into the key-value store.

    Returns lightweight descriptors carrying the store key instead of the
    payload, so the dataset record stays readable by a language model.
    """
    stored = []
    for index, image in enumerate(images or []):
        data_uri = image.get("data_uri") or ""
        _, _, payload = data_uri.partition(",")
        if not payload:
            continue
        key = f"image-{index}-{image.get('slug')}-{image.get('kind')}.png"
        await Actor.set_value(
            key, base64.b64decode(payload), content_type="image/png"
        )
        stored.append(
            {
                "slug": image.get("slug"),
                "kind": image.get("kind"),
                "bytes": image.get("bytes"),
                **_kvs_record_ref(key),
            }
        )
    return stored


async def _run_coverage_preview(base_url: str, headers: dict, inp: dict) -> None:
    """Free path: fetch and publish the coverage preview, charge nothing."""
    params = coverage_params(inp)
    url = f"{base_url}/api/partner/coverage"
    Actor.log.info("Requesting free coverage preview from %s", url)
    async with httpx.AsyncClient(timeout=COVERAGE_TIMEOUT_SECONDS) as http:
        resp = await http.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        await Actor.fail(
            status_message=(
                f"Coverage preview failed with HTTP {resp.status_code}: "
                f"{resp.text[:200]}"
            )
        )
        return
    record = coverage_record(resp.json())
    await Actor.push_data(record)
    Actor.log.info(
        "Preview: %s chapters, coverage '%s'.",
        record.get("chapterCount"),
        record.get("coverageLevel"),
    )


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

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "parcelabot-apify-actor/0.2",
            **_subscriber_headers(),
        }

        if inp.get("dryRun"):
            try:
                await _run_coverage_preview(base_url, headers, inp)
            except ValueError as exc:
                await Actor.fail(status_message=str(exc))
            return

        try:
            payload = build_payload(inp)
        except ValueError as exc:
            await Actor.fail(status_message=str(exc))
            return

        url = f"{base_url}/api/partner/reports"

        Actor.log.info("Requesting report from %s", url)
        resp = None
        last_error = ""
        # Transient upstream failures (network, 5xx, Catastro timeouts) are
        # worth a couple of quick retries before giving up.
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
                    resp = await http.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = f"request failed: {exc!r}"
                resp = None
            else:
                if resp.status_code < 500:
                    break  # 2xx / 4xx are final answers
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"

            if attempt < MAX_ATTEMPTS:
                Actor.log.warning(
                    "Attempt %d/%d failed (%s) — retrying in %ss",
                    attempt,
                    MAX_ATTEMPTS,
                    last_error,
                    RETRY_BACKOFF_SECONDS,
                )
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        if resp is None:
            await Actor.fail(
                status_message=f"Request to Parcelabot failed after "
                f"{MAX_ATTEMPTS} attempts: {last_error}"
            )
            return

        if resp.status_code != 200:
            detail = ""
            code = ""
            body = {}
            try:
                body = resp.json()
                detail = body.get("message") or resp.text
                code = body.get("error") or ""
            except Exception:
                detail = resp.text

            # An upstream quota response is a useful terminal outcome, not
            # an Actor failure. It is never a chargeable report result.
            if resp.status_code == 429:
                Actor.log.warning("Upstream quota reached: %s", detail)
                await Actor.push_data(quota_record(body))
                return

            # 422 = a valid "nothing to report here" answer (the point is not
            # on a parcel, or outside coverage). Finish cleanly with an
            # informative record rather than failing the whole run.
            if resp.status_code == 422:
                Actor.log.info("No report for this location: %s", detail)
                await Actor.push_data(
                    {
                        "status": "no_data",
                        "error": code or "no_parcel",
                        "message": detail,
                        "requested": {
                            "ref": payload.get("ref"),
                            "location": payload.get("location"),
                            "lat": payload.get("lat"),
                            "lng": payload.get("lng"),
                        },
                    }
                )
                return

            await Actor.fail(
                status_message=(
                    f"Parcelabot returned HTTP {resp.status_code}: {detail}"
                )
            )
            return

        data = resp.json()
        record = record_from_response(data)

        images = await _store_images(data.get("images") or [])
        if images:
            record["images"] = images

        markdown = record.pop("markdown", None)
        if markdown:
            # The prose lives in the key-value store; the dataset record
            # keeps the structured facts an agent actually parses.
            await Actor.set_value(
                "REPORT.md", markdown, content_type="text/markdown"
            )
            record["markdownKeyValueStoreKey"] = "REPORT.md"

        # Store and charge atomically: a user pays only when the ready report
        # is present in their dataset. The Apify Console defines the price.
        # ``charged_event_name`` is keyword-only in the Actor SDK.
        charge_result = await Actor.push_data(
            record, charged_event_name="report-generated"
        )
        if charge_result.event_charge_limit_reached:
            Actor.log.warning(
                "The report was delivered, but the run charge limit was reached."
            )
        Actor.log.info(
            "Report delivered (%s chapters, verdict '%s', cache %s).",
            record.get("chapterCount"),
            (record.get("summary") or {}).get("overall_verdict"),
            record.get("cache"),
        )


if __name__ == "__main__":
    asyncio.run(main())
