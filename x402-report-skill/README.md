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

## What's in a full report

One paid order returns a single Markdown document of **~20 parcel-level
chapters** compiled from official/authoritative sources — not a generic area
summary. Hazard and climate chapters rely on national/modelled data and are
**always computed**; POI-driven chapters fill in where local data exists
(that's exactly what the free coverage check tells you up front).

- **Hazards & risk** — flood risk (SNCZI zones), seismic zoning, radon
  potential (CSN), wildfire risk (EFFIS), mold risk, lightning density.
- **Climate & environment** — climate normals (AEMET/ERA5), wind rose,
  solar-PV potential (PVGIS), air quality (EEA), pollen calendar, light
  pollution, coastal sea-level rise.
- **Land & position** — cadastral identity, elevation/slope/aspect,
  historical-maps overlay.
- **Access & community** — critical-infrastructure proximity, public-transport
  access, tourism/culture/events, neighborhood sentiment (from real nearby
  Google Places reviews).

Each chapter is a short, sourced section with a plain-language takeaway, so the
whole document is directly quotable back to an end user.

> **Visual chapters embed images.** A few chapters (e.g. elevation/slope/aspect
> and the historical-maps overlay) include a **base64-encoded PNG inside inline
> HTML** — these render in any Markdown-with-HTML viewer or when converted to
> PDF. A text-only agent won't "see" the image, but still gets the sourced
> facts around it (sheet name, coordinates, source, takeaway). The overlay is
> also geography-gated (Spain MTN50, France état-major) and skipped cleanly
> where no historical layer exists.

### Sample (excerpt)

```markdown
## Flood Risk (SNCZI)
Risk band: **Low** — the parcel sits outside the 100- and 500-year modelled
flood envelopes (nearest zone ~640 m NE). Source: SNCZI.

## Radon
Potential: **High** (CSN zone 2). Consider a radon test before purchase;
mitigation is straightforward for new builds.
```

### Where we cover

- **Spain** — the full chapter set, including the foral provinces (Bizkaia,
  Gipuzkoa, Araba, Navarre).
- **Andorra, France, Netherlands** — a growing subset (global/EU datasets +
  country-aware hazard providers); Spain-only chapters are skipped cleanly
  rather than faked.

Call `GET /api/agent/coverage` to see the exact chapters for a coordinate
**before** paying.

### When it's worth ordering

- **Pre-purchase due diligence** on a specific home or plot — flood, radon,
  seismic and wildfire before an offer.
- **Relocation / expat vetting** — climate comfort, air quality, light
  pollution and mold risk for a shortlisted address.
- **Build or agro feasibility** — elevation/slope/aspect, solar and wind
  potential, wildfire exposure.
- **Insurance / underwriting triage** — a consistent hazard stack keyed to a
  coordinate.
- **Listing enrichment** — add an objective risk & amenity section to a
  property listing.
- **Portfolio screening at scale** — batch coordinates into structured risk
  profiles.

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
charged in the **token + network the 402 declares** — the client learns both
from the 402, so there is nothing to configure. Against the public Parcelabot
endpoint that is **USDC on Base mainnet (real funds)**. Testnet (Base Sepolia)
only applies if you run your **own** Parcelabot instance configured for it; you
cannot pay a mainnet server with testnet funds.

See [`reference.md`](reference.md) for the full API contract.
