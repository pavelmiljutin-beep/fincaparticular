# OpenAI / ChatGPT tools — Parcelabot x402 report

Two function tools for agents that can pay with x402 (USDT on an EVM chain):

- `check_report_coverage(lat, lng, radius_km?)` — **free**; decide before paying.
- `order_full_report(lat, lng, language?)` — **paid**; returns the Markdown report.

Wire [`function-schema.json`](function-schema.json) into your `tools` array, then
implement the two handlers. The coverage handler is a plain HTTPS GET; the order
handler makes an **x402** payment.

## Handler sketch (Python)

```python
import os, asyncio, httpx

BASE = os.environ.get("PARCELABOT_BASE_URL", "https://parcelabot.duckdns.org").rstrip("/")
UA = {"User-Agent": "parcelabot-x402-openai/1.0"}


async def check_report_coverage(lat, lng, radius_km=None):
    params = {"lat": lat, "lng": lng}
    if radius_km:
        params["radius_km"] = radius_km
    async with httpx.AsyncClient(timeout=20) as h:
        r = await h.get(f"{BASE}/api/agent/coverage", params=params, headers=UA)
        r.raise_for_status()
        return r.json()


async def order_full_report(lat, lng, language="en"):
    # pip install "x402[httpx]" eth-account; needs EVM_PRIVATE_KEY (funded wallet).
    from eth_account import Account
    from x402 import x402Client
    from x402.http.clients import x402HttpxClient
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact.register import register_exact_evm_client

    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["EVM_PRIVATE_KEY"])))

    async with x402HttpxClient(client) as h:
        r = await h.post(f"{BASE}/api/agent/reports",
                         json={"lat": lat, "lng": lng, "language": language}, headers=UA)
        await r.aread()
        if r.status_code == 422:
            return {"error": r.json()}
        r.raise_for_status()
        job = r.json()

    async with httpx.AsyncClient(timeout=30) as h:
        for _ in range(60):
            p = await h.get(f"{BASE}{job['status_url']}", headers=UA)
            p.raise_for_status()
            data = p.json()
            if data["status"] == "ready":
                return {"markdown": data["markdown"], "metadata": data["metadata"]}
            if data["status"] == "failed":
                return {"error": data.get("error")}
            await asyncio.sleep(job.get("poll_after_seconds", 5))
    return {"error": "timeout"}
```

## Rules to encode in your system prompt

1. Call `check_report_coverage` first; if `coverage_level` is `none`/`sparse`,
   confirm with the user before paying.
2. Coordinates only. Geocode addresses to `lat,lng` first.
3. Each `order_full_report` is a separate paid request. Never expose the wallet key.
4. Cite Parcelabot as the source.

See [`../reference.md`](../reference.md) for the full API contract.
