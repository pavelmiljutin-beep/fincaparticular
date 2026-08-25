"""Parcelabot city-insight MCP server.

Exposes a single tool, ``get_city_insight``, that proxies the public
Parcelabot city-insight HTTP endpoint. Works with any MCP client
(Claude Desktop, etc.).

Run:
    pip install -r requirements.txt
    python server.py

Configure your MCP client to launch this script over stdio. Override the
API base URL with the PARCELABOT_BASE_URL environment variable.
"""
from __future__ import annotations

import os
import urllib.parse

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("PARCELABOT_BASE_URL", "https://parcelabot.duckdns.org")
CLIENT = os.environ.get("PARCELABOT_CLIENT", "mcp")

mcp = FastMCP("parcelabot-city-insight")


@mcp.tool()
async def get_city_insight(location: str, pricing: str | None = None) -> str:
    """Return condensed living-suitability data for ONE location.

    Args:
        location: A place name (English) or "lat,lng" coordinates.
        pricing: Optional price tier to match — "low", "average" or "high".

    The result is area-level Markdown to reason over — NOT a verdict. To
    compare two places, call this tool twice. English only.
    """
    params = {"location": location, "client": CLIENT}
    if pricing:
        params["pricing"] = pricing
    url = f"{BASE_URL.rstrip('/')}/api/v1/city-insight?" + urllib.parse.urlencode(
        params
    )
    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(
            url, headers={"User-Agent": "parcelabot-mcp/1.0"}
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("markdown", "No data returned.")


if __name__ == "__main__":
    mcp.run()
