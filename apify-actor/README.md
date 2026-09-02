# Parcelabot Property Report — Apify Actor

A **thin proxy Actor** that orders a full, parcel-level Parcelabot property
due-diligence report and returns it as **Markdown**. It does no scraping and
runs no browser — it forwards your input to the Parcelabot host
(`parcelabot.duckdns.org`) and stores the result in the Actor's dataset.

Coverage: **Spain, France, Andorra, the Netherlands** (Spain has the full
chapter set; the others a growing subset). A report bundles ~20 chapters —
cadastral identity, flood/wildfire/seismic/radon hazards, climate, wind,
solar, air quality, noise, transport access, demographics and more.

## How it works

```
Apify run  ──►  POST https://parcelabot.duckdns.org/api/partner/reports
                  { location | lat,lng, language, persist }
                  Authorization: Bearer <PARCELABOT_API_KEY>
           ◄──  { markdown, metadata, price }   (one synchronous response)
```

The Actor pushes one item to the default **dataset** and writes the report
body to the key-value store record `REPORT.md`. Apify bills the run; the
Parcelabot server authenticates the Actor with a shared API key.

## Input

| Field | Type | Notes |
| --- | --- | --- |
| `location` | string | `"lat,lng"`, e.g. `40.4168,-3.7038`. Simplest option. |
| `lat`, `lng` | string | Decimal degrees, as an alternative to `location`. |
| `ref` | string | Exact cadastral reference — Spain (20-char RC), France (14-char IDU) or Netherlands (kadastrale aanduiding). Takes priority over coordinates. |
| `country` | enum | Optional `ES` / `FR` / `NL` to disambiguate an ambiguous `ref`. |
| `language` | enum | `en` (default), `es`, `fr`, `de`, `uk`, `ru`, `ar`. |
| `persist` | boolean | Ask the server to also store the report (default `false`). |
| `baseUrl` | string | Override the Parcelabot host (default is the public one). |
| `apiKey` | string (secret) | Partner API key. Prefer the env var below. |

### Example

```json
{
    "location": "40.4168,-3.7038",
    "language": "en"
}
```

## Authentication

Set a **secret environment variable** on the Actor (Console → Actor →
Settings → Environment variables), rather than putting the key in input:

```
PARCELABOT_API_KEY = <your partner key>
```

Optionally `PARCELABOT_BASE_URL` to point at a non-default host.

The matching server key is configured on Parcelabot via `PARTNER_API_KEYS`
(comma-separated), with `PARTNER_API_ENABLED=1`.

## Output

One dataset item per run:

| Field | Description |
| --- | --- |
| `markdown` | The full report as Markdown (also saved as `REPORT.md`). |
| `metadata` | `language`, `chapters`, `chapter_count`, `location`. |
| `ref`, `country`, `province`, `municipality`, `lat`, `lng` | Parcel identity. |
| `chapterCount`, `chapters` | Chapter summary. |
| `priceAmount`, `priceCurrency`, `pricePlan` | Informational price (Apify does the billing). |

If the coordinate is **not on a parcel** or **outside coverage**, the run
finishes successfully with a single `{ "status": "no_data", "error", "message",
"requested" }` item instead of failing — aim at a building rooftop and retry.


## Monetization

The Actor is billing-agnostic. To enable Apify **pay-per-event**, define the
event in the Actor's monetization settings and enable the charge hook in
[`src/main.py`](src/main.py) (`_maybe_charge` → `await Actor.charge(...)`).

## Build from GitHub

This Actor lives in the `ai-skills/apify-actor/` subdirectory of the
Parcelabot repository. When creating the Actor in Apify, link the Git repo
and set the **directory** to `ai-skills/apify-actor` so Apify uses this
`Dockerfile` and `.actor/` config.

## Local development

```bash
pip install apify-cli   # or: npm i -g apify-cli
cd ai-skills/apify-actor
# put your input in storage/key_value_stores/default/INPUT.json
export PARCELABOT_API_KEY=... PARCELABOT_BASE_URL=http://localhost:8000
apify run
```

Run the pure-logic tests without the SDK:

```bash
python -m pytest tests/
```
