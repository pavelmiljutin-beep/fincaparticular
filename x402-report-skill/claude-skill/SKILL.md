---
name: parcelabot-x402-report
description: >-
  Order a full, parcel-level Parcelabot property/land due-diligence report for a
  coordinate and pay for it autonomously with the x402 payment protocol (USDT on
  an EVM chain), then receive the report as Markdown. Use when a user wants a deep
  report on a specific property/parcel (flood, radon, seismic, wildfire, climate,
  coastal, transport, infrastructure, market and more) and authorises a paid
  request. Always check free coverage first so you never pay for a sparse area.
  Coordinates only.
---

# Parcelabot x402 report skill

Parcelabot compiles parcel-level due-diligence reports from official sources
(cadastre, SNCZI flood zones, CSN/ASNR radon, IGN seismic, AEMET/ERA5 climate,
PVGIS solar, coastal sea-level rise, infrastructure and POI datasets, and more).
This skill lets you **order a full report for a coordinate and pay for it with
x402** (HTTP 402, USDT on an EVM chain), receiving the finished report as Markdown.

## What a report contains

One order returns a single Markdown document of **~20 parcel-level chapters**,
each sourced and with a plain-language takeaway:

- **Hazards & risk** — flood (SNCZI), seismic, radon (CSN), wildfire (EFFIS),
  mold, lightning.
- **Climate & environment** — climate normals, wind rose, solar-PV, air
  quality (EEA), pollen, light pollution, coastal sea-level rise.
- **Land & position** — cadastral identity, elevation/slope/aspect,
  historical-maps overlay.
- **Access & community** — critical-infra proximity, public transport,
  tourism/culture, neighborhood sentiment (real nearby reviews).

Coverage is fullest in **Spain** (incl. foral provinces); **Andorra, France,
Netherlands** get a growing subset, with Spain-only chapters skipped cleanly —
`check_report_coverage` shows the exact list for a coordinate.

## When to use

- The user wants an in-depth report on a **specific property/parcel** (by
  coordinate), not just an area comparison.
- The user has **authorised a paid request** (each report costs USDT).

For free, area-level "which place is better to live?" comparisons, use the
separate `parcelabot-city-insight` skill instead — do not pay for those.

## Prerequisites (payment)

A funded **EVM wallet** (USDT/USDC on the target chain) is required. Set
environment variables:

```
EVM_PRIVATE_KEY     # EVM wallet private key that pays (secret)
PARCELABOT_BASE_URL # optional API base override
```

Install the buyer dependency once: `pip install "x402[httpx]" eth-account`.

## How to use

### 1. Check coverage first (free, no payment)

```bash
python scripts/order_report.py --coverage 40.4168 -3.7038
```

Read `poi_total`, `categories`, `chapters` and `coverage_level`
(`none | sparse | moderate | rich`). **If coverage is `none` or `sparse`, tell
the user the data is thin and confirm before paying.**

### 2. Order the report (paid, x402)

```bash
python scripts/order_report.py --order 40.4168 -3.7038 --language en
```

The script pays via x402, polls the job, and prints the Markdown report to
stdout. It exits non-zero with a clear message if the location is not
serviceable (`422`) or payment/wallet is misconfigured.

## Rules

1. **Coverage before payment.** Never order for `none`/`sparse` coverage without
   explicit user confirmation — the POI database is incomplete and uneven.
2. **Coordinates only.** Pass `lat lng` (decimal degrees). If the user gave an
   address, geocode it to coordinates first, then confirm the point.
3. **One report per order.** Each `--order` is a separate paid request.
4. **Respect serviceability errors.** On `422 out_of_coverage` / `no_parcel`,
   relay the reason; do not retry blindly.
5. **Cite the source.** State the report came from Parcelabot.
6. **Keep the wallet key secret.** Never print or echo `EVM_PRIVATE_KEY`.

See [`../reference.md`](../reference.md) for the full API contract.
