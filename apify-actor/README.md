# Parcelabot Property Report — Apify Actor

Parcel-level property due-diligence for **Spain, France, Andorra and the
Netherlands**, returned as **structured JSON facts** an agent can act on
directly. It does no scraping and runs no browser — it forwards your input to
the Parcelabot host and stores the result in the Actor's dataset.

**Look before you buy:** run once with `dryRun: true` for a **free** preview of
which chapters exist at that location, how dense the local data is, and how
many bytes/tokens each output format would cost you. Then order the report.

## What you get

A report bundles ~20 chapters — cadastral identity, flood / wildfire / seismic
/ radon hazards, climate, wind, solar, air quality, noise, transport access,
demographics and more. Each chapter comes back as:

```json
{
  "slug": "flood-risk-snczi",
  "title": "Flood risk",
  "category": "hazards",
  "verdict": "unfavorable",
  "band": "high",
  "headline": "Unfavorable",
  "metrics": [
    { "key": "in_zfp", "value": true },
    { "key": "in_dph", "value": false }
  ],
  "source": { "name": "SNCZI / MITECO", "as_of": "2026-08-20T10:00:00+00:00" }
}
```

plus a top-level `summary` you can decide on in a few hundred tokens:

```json
{
  "overall_verdict": "unfavorable",
  "red_flags": [{ "slug": "flood-risk-snczi", "band": "high" }],
  "green_flags": [{ "slug": "wildfire-risk-effis", "band": "none" }],
  "chapters_ok": 21,
  "chapters_failed": [],
  "chapters_skipped": ["old-maps-overlay"]
}
```

`chapters_failed` matters: it distinguishes *"nothing to flag here"* from
*"an upstream source was down"*, so you can retry instead of drawing the wrong
conclusion. Entries carry `retryable`.

## When **not** to use this

* You need a legal document — this is informational screening, not a *nota
  simple*, PPRi zoning, or an official cadastral extract.
* Your point is not on a building or plot. A plaza, road, park or stretch of
  water has no cadastral parcel and returns `status: "no_data"`.
* You are outside Spain, France, Andorra or the Netherlands.
* You want a live feed. Chapters are screening snapshots with an `as_of` date.

## How it works

```
dryRun   ──►  GET  /api/partner/coverage?lat=..&lng=..      (free)
         ◄──  { chapters, coverage_level, size_estimates }

report   ──►  POST /api/partner/reports
                { location | lat,lng | ref, format, detail,
                  chapters, includeImages, language }
         ◄──  { summary, chapters, metadata, price }   (one sync response,
                                                        typically 20–30 s)
```

## Input

| Field | Type | Notes |
| --- | --- | --- |
| `dryRun` | boolean | **Free** coverage preview instead of a report. Needs coordinates. |
| `location` | string | `"lat,lng"`, e.g. `40.4168,-3.7038`. Simplest option. |
| `lat`, `lng` | string | Decimal degrees, as an alternative to `location`. |
| `ref` | string | Exact cadastral reference — Spain (20-char RC), France (14-char IDU) or Netherlands (kadastrale aanduiding). Takes priority over coordinates. |
| `country` | enum | Optional `ES` / `FR` / `NL` to disambiguate an ambiguous `ref`. |
| `format` | enum | `json` (default), `markdown`, `both`. |
| `detail` | enum | `full` (default) or `brief` — verdicts and headlines only, no metrics. Applies to the JSON facts. |
| `chapters` | array | Only these chapter slugs. Prerequisites are added automatically and listed in `metadata.chapters_auto_added`. |
| `excludeChapters` | array | Drop specific chapter slugs. |
| `includeImages` | boolean | Default `false`. See *Images* below. |
| `language` | enum | `en` (default), `es`, `fr`, `de`, `uk`, `ru`, `ar`. |
| `radiusKm` | string | Dry run only: POI search radius. |
| `persist` | boolean | Ask the server to also store the report (default `false`). |
| `baseUrl` | string | Override the Parcelabot host (default is the public one). |
| `apiKey` | string (secret) | Partner API key. Prefer the env var below. |

### Examples

Free preview:

```json
{ "location": "40.4168,-3.7038", "dryRun": true }
```

Full report:

```json
{ "location": "40.4168,-3.7038", "format": "json" }
```

Just the two hazards you care about, minimal payload:

```json
{
    "location": "40.4168,-3.7038",
    "chapters": ["flood-risk-snczi", "seismic-zoning-ign"],
    "detail": "brief"
}
```

## Images

Map images are large base64 PNGs — a single one can outweigh the entire text
report — so they are **off by default**. With `includeImages: true` they are
written to the key-value store and referenced from the dataset record
(`images[].keyValueStoreKey`) rather than inlined, keeping the record readable
by a language model. When Apify exposes the default store id, each descriptor
also carries `keyValueStoreId` and an `apiUrl` of the form
`https://api.apify.com/v2/key-value-stores/{storeId}/records/{key}`. Fetch that
URL with an Apify token that can read the run storage, or open the key from the
run's Key-value store tab in Console.

Image-only chapters such as `old-maps-overlay` are omitted from default
image-free report runs; request `includeImages: true` when those visual artifacts
are part of the due diligence decision.

Markdown output is likewise stored as `REPORT.md` and referenced by
`markdownKeyValueStoreKey`.

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

One dataset item per run.

**Report run** (`status: "ready"`):

| Field | Description |
| --- | --- |
| `summary` | Overall verdict, red/green flags, chapter counts. Read this first. |
| `chapters` | Per-chapter facts: verdict, band, metrics, source. |
| `metadata` | `language`, `format`, `detail`, `chapters`, `chapters_failed`, `chapters_skipped`, `chapters_auto_added`, `location`. |
| `ref`, `country`, `province`, `municipality`, `lat`, `lng` | Parcel identity. |
| `chapterCount`, `chapterSlugs` | Chapter summary. |
| `chaptersFailed`, `chaptersSkipped` | Completeness. `retryable` marks transient failures. |
| `cache` | `"miss"` (freshly generated) or `"hit"` (replayed); `cachedAt` gives the original timestamp. |
| `markdownKeyValueStoreKey` | Present when Markdown was requested (`REPORT.md`). |
| `images` | Present when `includeImages` — descriptors with `keyValueStoreKey`, and usually `keyValueStoreId` + `apiUrl`. |
| `priceAmount`, `priceCurrency`, `pricePlan` | Informational unit price. |

**Dry run** (`status: "preview"`): `coverageLevel`, `poiTotal`, `chapterCount`,
`chapters`, `chaptersUnavailable`, `sizeEstimates`, `datasets`, `categories`.

`sizeEstimates` gives `estimated_bytes` / `estimated_tokens` for each
`(format, detail)` pair, plus `estimated_bytes_with_images`, so you can pick a
format that fits your context budget before ordering.

### Error taxonomy

| Outcome | Meaning | What to do |
| --- | --- | --- |
| `status: "no_data"` (run succeeds) | Not on a parcel, or outside coverage. `error` is `no_parcel`, `out_of_coverage` or `bad_location`. | Aim at a building rooftop and retry. Not retryable as-is. |
| `status: "quota_exceeded"` (run succeeds) | Fair-use cap reached. `quotaWindow`, `quotaUsed`, `quotaLimit`, `quotaResetsAt`. | Wait until `quotaResetsAt`. Cache hits and dry runs still work. |
| HTTP 400 `bad_request` | Unknown chapter slug or format. | Fix the input. |
| HTTP 503 `upstream_unavailable` | A source (e.g. the cadastre) timed out. | Transient — the Actor already retries 3×; retry the run later. |
| `chapters_failed[]` non-empty | The report built, but some chapters did not. | Treat those chapters as unknown, not as clean. |

## Caching

An identical request — same location, language, format, detail, chapter set
and image setting — replays the stored report instead of re-querying every
upstream source. Hits are near-instant, and they do **not** count against the
fair-use cap, so re-reading a report you already ordered is free.

Coordinates are rounded to about 11 m before matching, so two agents aiming at
the same rooftop share a result while neighbouring parcels stay distinct.
Changing any option that changes the output produces a fresh report.

## Pricing

This Actor is intended for Apify's **pay-per-event** model, not rental pricing.
Configure one primary event in the Apify Console:

| Event | Launch price | Charged when | Not charged |
| --- | --- | --- | --- |
| `report-generated` | **$0.49 / report** | A full report is successfully returned (`status: "ready"`), including a cache hit. | Free `dryRun` coverage previews, `no_data`, quota responses, invalid input, and failed runs. |

$0.49 is a deliberately low adoption price for a structured, multi-source
parcel-screening report. It is easy to understand, avoids charging for a
location that cannot produce a report, and leaves room to move toward
$0.79–$0.99 after 100 paid reports and a measured cost/reliability review.
Enable pass-through platform usage costs only if Apify Analytics shows them
materially eroding the margin; the report event remains the only user-facing
price signal.

The server's `priceAmount`, `priceCurrency`, and `pricePlan` fields remain
informational metadata about Parcelabot's underlying service, not the Apify
charge. The older `quota_exceeded` status is retained for backwards-compatible
handling of any server-side quota policy; it is not part of this Actor's launch
pricing.

If you would rather pay per report in USDC, Parcelabot also exposes an
[x402 rail](../x402-report-skill/) that takes crypto payment directly, with the
same free coverage preview.

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
