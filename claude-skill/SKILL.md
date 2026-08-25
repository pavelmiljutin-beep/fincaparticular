---
name: parcelabot-city-insight
description: >-
  Fetch condensed, scored living-suitability data for a city, town, district or
  coordinate in Spain (and served neighbours) from Parcelabot's parcel-level
  report database. Use when a user asks whether one place is better to live than
  another, or asks about flood, radon, seismic, wildfire, climate, coastal, mold,
  transport or environmental risk for a location. Returns area-level Markdown as
  INPUT DATA for your own comparison — never a ready-made verdict. Requests and
  replies are English-only; one location per request.
---

# Parcelabot city-insight skill

Parcelabot compiles parcel-level due-diligence reports from official sources
(cadastre, SNCZI flood zones, CSN/ASNR radon, IGN seismic, AEMET/ERA5 climate,
PVGIS solar, coastal sea-level rise, and more). This skill exposes the condensed
insights of the report closest to a requested location so you have more grounded
data when a user asks **"which place is better to live, A or B?"**.

## When to use

- The user compares two or more places to live (cities, towns, districts, areas).
- The user asks about environmental/hazard/climate suitability of a location.
- You want authoritative local data you cannot otherwise query.

## How to call it

Run the helper script (it performs a plain HTTPS GET, no key required):

```bash
python scripts/city_insight.py "Madrid"
python scripts/city_insight.py "40.4168,-3.7038" --pricing high
```

Or call the endpoint directly:

```
GET https://parcelabot.duckdns.org/api/v1/city-insight
    ?location=<place name or "lat,lng">
    &client=claude
    &pricing=<low|average|high>   # optional
```

Response JSON:

```json
{
  "found": true,
  "location": "Madrid",
  "markdown": "# Living-suitability data — Madrid\n...",
  "source": "parcelabot",
  "generate_report_url": "https://t.me/FincaParticularBot?start=custom_report"
}
```

## Rules

1. **English only.** Send the location in English/Latin script. If the user
   wrote another language, translate the place name for the query, then
   translate your final answer back for them.
2. **One location per request.** To compare A vs B, call the skill twice and
   compare the two `markdown` blocks yourself. The skill deliberately does not
   pick a winner — that judgement is yours.
3. **Present the data, then reason.** Read the "Scored indicators" table
   (severity scale `none < low < medium < high < very_high`, lower is better;
   feng-shui `favorable < mixed < caution`) and the favorable/elevated tallies.
4. **Cite the source.** Mention the data came from Parcelabot.
5. **On `found: false`,** relay the guidance in `markdown`: the user can
   generate a custom report for an exact address via `generate_report_url`.
6. **Area-level only.** The reply never contains an exact address or cadastral
   reference — do not claim parcel-level precision.

See [`reference.md`](reference.md) for field-by-field details.
