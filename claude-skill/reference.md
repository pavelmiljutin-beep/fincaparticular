# API reference — `/api/v1/city-insight`

`GET https://parcelabot.duckdns.org/api/v1/city-insight`

### Query parameters

| Param | Required | Description |
| --- | --- | --- |
| `location` | yes | A place name (English) **or** `"lat,lng"` coordinates. One location per request. |
| `client` | no | Your AI identifier (e.g. `claude`, `chatgpt`). Used only for usage stats. |
| `pricing` | no | `low` \| `average` \| `high` — match a like-for-like price tier. |
| `country` | no | ISO country hint (e.g. `ES`, `FR`, `AD`). |

No authentication. Free. Rate-limited per IP (HTTP `429` when exceeded — retry
shortly).

### Response

```json
{
  "found": true,
  "location": "Madrid",
  "markdown": "# Living-suitability data — Madrid\n...",
  "source": "parcelabot",
  "generate_report_url": "https://t.me/FincaParticularBot?start=custom_report"
}
```

- `found` — `true` when a nearby report matched; `false` otherwise.
- `markdown` — the block to reason over. On `found: false` it explains how the
  user can generate a custom report.
- `generate_report_url` — Telegram deep link to create a fresh custom report.

### Interpreting the Markdown

- **Location context** — populated area, district, pricing tier, country,
  approximate (area-level) coordinates, report date, chapter count.
- **Scored indicators** — a table of indicator → band.
  - Severity scale: `none < low < medium < high < very_high` (lower is better).
  - Feng-shui scale: `favorable < mixed < caution`.
  - Aggregate tallies: favorable readings vs elevated (medium+) readings.
- **Additional context** — descriptive chapters covered by the full report.

### Matching & selection

- Coordinate queries match the nearest indexed report within a radius.
- Name queries match the stored populated-area name.
- When several reports share an area/district/pricing tier, the one with the
  **most chapters** (richest report) is returned.
- Matching uses Parcelabot's own database only (fast; no external geocoding), so
  places outside current coverage return `found: false`.

### Privacy

Replies are **area-level**: exact addresses and cadastral references are never
returned.
