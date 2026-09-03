# Parcelabot x402 report skill

An AI-agent skill for **ordering a full, parcel-level Parcelabot property report
and paying for it autonomously with the [x402](https://docs.x402.org) payment
protocol** (HTTP 402, **a USD stablecoin — USDC by default — on an EVM chain**).
The agent receives the finished report as **structured JSON facts** by default,
or as Markdown prose on request.

This is the paid, machine-to-machine counterpart to the free
[`../` city-insight skills](../README.md): humans use the Telegram bot; agents
use x402.

## What an agent can do

| Step | Endpoint | Payment | Purpose |
| --- | --- | --- | --- |
| 1. Preview coverage | `GET /api/agent/coverage` | **free** | See which chapters exist near a coordinate, how much local data backs them, and how many bytes/tokens each output format would cost — so you decide whether to order. |
| 2. Order a report | `POST /api/agent/reports` | **x402 (paid)** | Pay per report; returns a `job_id`. |
| 3. Collect the report | `GET /api/agent/reports/{job_id}` | free | Poll until `status: ready`; read `summary` + `chapters` (and `markdown` if you asked for it). |

Base URL (configurable): `https://parcelabot.duckdns.org`

### Request options

`POST /api/agent/reports` accepts, alongside `lat`/`lng` and `language`:

| Field | Default | Effect |
| --- | --- | --- |
| `format` | `json` | `json` (per-chapter facts), `markdown` (prose), or `both`. |
| `detail` | `full` | `brief` keeps only each chapter's verdict and headline. |
| `chapters` | all | Limit to specific slugs; prerequisites are added automatically and reported in `metadata.chapters_auto_added`. |
| `excludeChapters` | — | Drop specific slugs. |
| `includeImages` | `false` | See the images note below. |

The JSON envelope gives each chapter a `verdict`
(`favorable`/`mixed`/`unfavorable`/`unknown`), the raw source `band`, a
`metrics` list with units, and a `source` with an `as_of` date — plus a
top-level `summary` carrying `overall_verdict`, `red_flags` and `green_flags`.
`metadata.chapters_failed` distinguishes *"nothing to flag here"* from *"an
upstream source was down"*, so a transient outage is never read as a clean
result.

## What's in a full report

One paid order covers **~20 parcel-level chapters** compiled from
official/authoritative sources — not a generic area summary. Hazard and climate
chapters rely on national/modelled data and are **always computed**; POI-driven
chapters fill in where local data exists (that's exactly what the free coverage
check tells you up front).

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

> **Map images are opt-in.** A few chapters (cadastral identity, the
> historical-maps overlay, radon) can carry a base64-encoded PNG. One of those
> can outweigh the entire text report, so they are **omitted unless you set
> `includeImages: true`** — in which case they arrive as an `images` array of
> descriptors rather than inlined into the prose. Without them you still get
> every sourced fact around the image (sheet name, coordinates, source,
> takeaway).

### Sample chapter (JSON)

```json
{
  "slug": "flood-risk-snczi",
  "title": "Flood risk",
  "category": "hazards",
  "verdict": "favorable",
  "band": "low",
  "metrics": [
    { "key": "in_any_band", "value": false },
    { "key": "in_zfp", "value": false }
  ],
  "source": { "name": "SNCZI / MITECO", "as_of": "2026-08-20T10:00:00+00:00" }
}
```

### Sample (Markdown excerpt)

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
thin report by mistake. It also returns `size_estimates` — `estimated_bytes`
and `estimated_tokens` for every `(format, detail)` pair, plus
`estimated_bytes_with_images` — so you can check the report fits your context
budget before committing. Check coverage first; order only if the data
justifies it.

## Recommended flow

1. `check_report_coverage(lat, lng)` → inspect `poi_total`, `categories`,
   `chapters`, `coverage_level`, `size_estimates`.
2. If coverage is worthwhile, `order_full_report(lat, lng, language)` — this
   handles the x402 payment automatically and returns the report.
3. Read `summary` first; drill into `chapters` only where a flag warrants it.
4. Present the findings; cite Parcelabot as the source.

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
