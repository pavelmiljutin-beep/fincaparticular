# Parcelabot x402 report API — reference

Machine-to-machine API for autonomous agents. Humans use the Telegram bot; this
API is payment-gated with [x402](https://docs.x402.org) over an EVM chain (a USD
stablecoin, USDC by default).

Base URL (configurable): `https://parcelabot.duckdns.org`

---

## 1. `GET /api/agent/coverage` — free

How much real data exists near a coordinate. No payment; rate-limited per IP.

Query parameters:

| Param | Required | Type | Notes |
| --- | --- | --- | --- |
| `lat` | yes | float | −90..90 |
| `lng` | yes | float | −180..180 |
| `radius_km` | no | float | 0..50; default from server config (~5 km) |

Response `200`:

```json
{
  "source": "parcelabot",
  "lat": 40.4168,
  "lng": -3.7038,
  "radius_km": 5.0,
  "poi_total": 37,
  "chapters_expected": 22,
  "coverage_level": "rich",
  "datasets": [
    { "id": "datacenters", "label": "Data centers", "category": "Infrastructure", "count": 2 },
    { "id": "public_transport", "label": "Public transport stops", "category": "Access & places", "count": 11 }
  ],
  "categories": [
    { "category": "Access & places", "count": 19 },
    { "category": "Infrastructure", "count": 12 }
  ],
  "chapters": [
    { "slug": "flood-risk-snczi", "title": "Flood Risk", "category": "hazards",
      "coverage": "computed at report time (national / modelled data)" }
  ],
  "chapters_unavailable": [
    { "slug": "land-registry-nota-simple", "title": "Land Registry — Nota Simple",
      "reason": "not_available" }
  ],
  "size_estimates": [
    { "format": "json", "detail": "brief", "estimated_bytes": 4840,
      "estimated_tokens": 1613, "estimated_bytes_with_images": 544840 },
    { "format": "json", "detail": "full", "estimated_bytes": 19800,
      "estimated_tokens": 6600, "estimated_bytes_with_images": 559800 },
    { "format": "markdown", "detail": "full", "estimated_bytes": 83600,
      "estimated_tokens": 20900, "estimated_bytes_with_images": 623600 }
  ]
}
```

Interpretation:

- `poi_total` — nearby points of interest across all bundled snapshots.
- `datasets` / `categories` — per-source and per-category counts (honest; may be `0`).
- `chapters` — report chapters that would be generated. Hazard/climate chapters
  are `computed at report time` (national/modelled), so they appear regardless
  of local POI density.
- `chapters_unavailable` — chapters we do **not** offer here, so "absent" is
  never mistaken for "checked and clean".
- `size_estimates` — forecast payload size per `(format, detail)` pair. Use it
  to pick a format that fits your context budget; note how much
  `estimated_bytes_with_images` adds, which is why images are opt-in.
- `coverage_level` — `none | sparse | moderate | rich`. Use it to decide whether
  ordering a paid report is worthwhile. **`none`/`sparse` means thin data.**

---

## 2. `POST /api/agent/reports` — x402 paid

Order one full report. Enforced by x402: an unpaid request returns
`402 Payment Required` with a base64 `PAYMENT-REQUIRED` header; retry with a
signed `PAYMENT-SIGNATURE` header (x402 client SDKs do this automatically).

Request body (JSON):

```json
{ "lat": 40.4168, "lng": -3.7038, "language": "en", "format": "json" }
```

or `{ "location": "40.4168,-3.7038", "language": "en" }`. Supported
`language` values: `en, es, ru, fr, uk, de, ar` (default `en`). Only coordinates
are accepted (most reliable for agents).

Optional output controls:

| Field | Default | Effect |
| --- | --- | --- |
| `format` | `json` | `json` — structured per-chapter facts; `markdown` — prose; `both`. |
| `detail` | `full` | `brief` drops `metrics` and `source`, keeping the verdict and headline. Applies to JSON only. |
| `chapters` | all | Array (or comma-separated string) of slugs. Dependencies are resolved automatically — asking for `mold-risk` also schedules `climate-normals-aemet` and `wind-rose`, reported back in `metadata.chapters_auto_added`. |
| `excludeChapters` | — | Slugs to drop. |
| `includeImages` | `false` | Include base64 map PNGs. One can outweigh the whole text report. |

An unknown slug or format returns `400 bad_request`.

On success `202 Accepted`:

```json
{
  "job_id": "3f9a...",
  "status": "pending",
  "status_url": "/api/agent/reports/3f9a...",
  "poll_after_seconds": 5,
  "price": { "amount": "3.00", "currency": "USD", "plan": "ai-agent" }
}
```

Errors:

- `422` `{ "error": "bad_location" | "out_of_coverage" | "no_parcel", ... }` —
  the parcel is not serviceable. This check runs **before** work begins.
- `503` `{ "error": "upstream_unavailable", ... }` — transient; retry later.

Payment settles for serviceable requests only. Payment is per report; keep the
`job_id`.

---

## 3. `GET /api/agent/reports/{job_id}` — free

Poll until the report is ready. No payment.

While rendering:

```json
{ "job_id": "3f9a...", "status": "processing", "poll_after_seconds": 5, "source": "parcelabot" }
```

When ready:

```json
{
  "job_id": "3f9a...",
  "status": "ready",
  "source": "parcelabot",
  "summary": {
    "overall_verdict": "mixed",
    "red_flags": [],
    "green_flags": [
      { "slug": "wildfire-risk-effis", "title": "Wildfire risk", "band": "none",
        "headline": "Favorable" }
    ],
    "chapters_ok": 22,
    "chapters_failed": [],
    "chapters_skipped": ["old-maps-overlay"]
  },
  "chapters": [
    {
      "slug": "flood-risk-snczi",
      "title": "Flood risk",
      "category": "hazards",
      "verdict": "favorable",
      "band": "low",
      "headline": "Favorable",
      "metrics": [{ "key": "in_zfp", "value": false }],
      "source": { "name": "SNCZI / MITECO", "as_of": "2026-08-20T10:00:00+00:00" },
      "status": "ok"
    }
  ],
  "metadata": {
    "language": "en",
    "format": "json",
    "detail": "full",
    "generated_at": "2026-08-20T10:00:00+00:00",
    "chapters": ["cadastral-identity", "flood-risk-snczi", "..."],
    "chapter_count": 22,
    "chapters_failed": [],
    "chapters_skipped": ["old-maps-overlay"],
    "images_included": false,
    "location": { "lat": 40.41, "lng": -3.70, "ref": "...", "province": "Madrid", "country": "ES" }
  }
}
```

`markdown` is present only when you asked for `format: "markdown"` or `"both"`;
`images` only with `includeImages: true`.

Reading the envelope:

- `summary` first — it is designed to settle a go/no-go in a few hundred tokens.
- `verdict` is one of `favorable | mixed | unfavorable | unknown`; `band` is the
  raw source classification behind it.
- `chapters_failed[]` carries `{slug, reason, retryable}`. A chapter listed here
  is **unknown**, not clean — retry rather than concluding from its absence.
- `status: "prose_only"` on a chapter means we do not model its numbers yet.

On failure: `{ "status": "failed", "error": "..." }`.

`status` values: `pending | processing | ready | failed`. Poll every
`poll_after_seconds`; a report typically finishes within a couple of minutes.

---

## Payment (x402 / EVM / USDC by default)

- Network: EVM (e.g. `eip155:84532` Base Sepolia testnet, `eip155:8453` Base
  mainnet); token is the chain's default stablecoin — USDC by default (6
  decimals) — or whatever token the server advertises. The client reads the
  network and asset from the 402.
- Client: `pip install "x402[httpx]" eth-account`, register the EVM scheme
  (`register_exact_evm_client`) with an `eth-account` signer, then use
  `x402HttpxClient` to POST — 402 handling is automatic.
- Settlement uses the public x402.org facilitator (testnets) or a managed one
  (mainnet). **No TON facilitator.** Clients need only a funded EVM wallet.

## Etiquette

- **Check coverage before ordering.** Don't pay for `none`/`sparse` areas unless
  you accept a thin report.
- Send a descriptive `User-Agent` (e.g. `parcelabot-x402-skill/1.0`).
- Cite Parcelabot as the data source in your answer.
