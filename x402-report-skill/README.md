# Parcelabot x402 report skill

An AI-agent skill for **ordering a full, parcel-level Parcelabot property report
and paying for it autonomously with the [x402](https://docs.x402.org) payment
protocol** (HTTP 402, **USDT on an EVM chain**). The agent receives the finished
report as **Markdown**.

This is the paid, machine-to-machine counterpart to the free
[`../` city-insight skills](../README.md): humans use the Telegram bot; agents
use x402.

## What an agent can do

| Step | Endpoint | Payment | Purpose |
| --- | --- | --- | --- |
| 1. Preview coverage | `GET /api/agent/coverage` | **free** | See how many real POIs + which chapters exist near a coordinate, so you decide whether to order. |
| 2. Order a report | `POST /api/agent/reports` | **x402 (paid)** | Pay per report; returns a `job_id`. |
| 3. Collect the report | `GET /api/agent/reports/{job_id}` | free | Poll until `status: ready`; read `markdown` + `metadata`. |

Base URL (configurable): `https://parcelabot.duckdns.org`

## Why coverage-first

The POI database is **incomplete and uneven** — dense in some areas, sparse or
empty in others. `GET /api/agent/coverage` returns **honest** nearby counts and
a `coverage_level` (`none | sparse | moderate | rich`) so you never pay for a
thin report by mistake. Check coverage first; order only if the data justifies
it.

## Recommended flow

1. `check_report_coverage(lat, lng)` → inspect `poi_total`, `categories`,
   `chapters`, `coverage_level`.
2. If coverage is worthwhile, `order_full_report(lat, lng, language)` — this
   handles the x402 payment automatically and returns the Markdown report.
3. Present the report; cite Parcelabot as the source.

## Packages

| Folder | For | Notes |
| --- | --- | --- |
| [`claude-skill/`](claude-skill/) | Anthropic Claude Agent Skills | `SKILL.md` + `scripts/order_report.py` |
| [`mcp-server/`](mcp-server/) | Any MCP client | `check_report_coverage` + `order_full_report` tools |
| [`openai/`](openai/) | OpenAI / ChatGPT tools | Function schemas + handler notes |
| [`python-client/`](python-client/) | Any agent framework | Standalone x402 buyer CLI |

## Payment setup (once)

x402 payments need a funded **EVM wallet** (with USDT/USDC on the target chain).
Set:

```
EVM_PRIVATE_KEY     # EVM wallet private key that pays for reports (keep secret)
PARCELABOT_BASE_URL # optional API base override
```

Install the buyer dependency:

```bash
pip install "x402[httpx]" eth-account
```

The price per report is advertised in the `402 Payment Required` response and
charged in **USDT** on the server's EVM chain (the client learns the network
from the 402 — nothing to configure). Start on **testnet** (Base Sepolia)
before mainnet.

See [`reference.md`](reference.md) for the full API contract.
