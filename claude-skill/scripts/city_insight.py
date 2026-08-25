#!/usr/bin/env python3
"""Fetch Parcelabot city-insight data for one location (stdlib only).

Usage:
    python city_insight.py "Madrid"
    python city_insight.py "40.4168,-3.7038" --pricing high
    python city_insight.py "Valencia" --base-url https://example.org

Prints the Markdown block the assistant should reason over. English only;
one location per call — call twice to compare two places.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://parcelabot.duckdns.org"
CLIENT = "claude"


def fetch(location: str, *, base_url: str, pricing: str | None) -> dict:
    params = {"location": location, "client": CLIENT}
    if pricing:
        params["pricing"] = pricing
    url = f"{base_url.rstrip('/')}/api/v1/city-insight?" + urllib.parse.urlencode(
        params
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "parcelabot-claude-skill/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("location", help='Place name or "lat,lng"')
    parser.add_argument("--pricing", choices=["low", "average", "high"])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()

    try:
        data = fetch(args.location, base_url=args.base_url, pricing=args.pricing)
    except Exception as exc:  # noqa: BLE001 — surface any network error plainly
        print(f"Error fetching city-insight: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data.get("markdown", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
