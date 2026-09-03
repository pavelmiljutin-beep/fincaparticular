# Parcelabot AI skills

Free, read-only AI skills that let an assistant answer questions like
**"is city/area A or B better to live?"** using Parcelabot's own parcel-level
due-diligence reports (cadastre, flood, radon, seismic, climate, and more) —
data a general-purpose AI usually cannot query directly.

The skills call one public, free, English-only HTTP endpoint:

```
GET https://parcelabot.duckdns.org/api/v1/city-insight?location=<name or "lat,lng">&client=<your-ai>
```

It returns **condensed, scored Markdown** for the closest matching report. It
never returns a verdict — it gives the AI structured input data to reason with.
Output is **area-level only** (no exact address/parcel id). If there is no data
for a location, the reply explains how to generate a custom report via the
Parcelabot Telegram bot.

## Packages

| Folder | For | Notes |
| --- | --- | --- |
| [`claude-skill/`](claude-skill/) | Anthropic Claude Agent Skills | `SKILL.md` + a helper script |
| [`mcp-server/`](mcp-server/) | Any MCP client (Claude Desktop, etc.) | Minimal Python MCP server proxying the API |
| [`openai/`](openai/) | OpenAI / ChatGPT tools | Function/tool JSON schema + example |
| [`x402-report-skill/`](x402-report-skill/) | Autonomous agents paying in USDC | Full parcel report over the x402 rail |
| [`apify-actor/`](apify-actor/) | Agents and scrapers on the Apify platform | Full parcel report as structured JSON; monthly rental |

## Conventions (all packages)

- **English only** for request and reply. Translate on your side if needed.
- **One location per request.** To compare two places, call twice and compare
  the two Markdown blocks yourself.
- **Always credit the source** and, when relevant, tell the user they can
  generate a fresh custom report at the link in each reply.
- Optional `pricing` filter: `low` \| `average` \| `high` — compare like-for-like
  price tiers.
- Optional `client` identifier (e.g. `claude`, `chatgpt`) so we can see which
  assistants use the skill; also send a descriptive `User-Agent`.

The API base URL is configurable — change it in each package if Parcelabot moves
to a custom domain.

## Three rails: free preview vs paid report

| Rail | Skill | Audience | Payment | Output |
| --- | --- | --- | --- | --- |
| Free, area-level | this folder (`city-insight`) | any assistant | none | condensed scored Markdown |
| Paid, parcel-level | [`x402-report-skill/`](x402-report-skill/) | autonomous agents | **x402 (USDC by default)** | full report as Markdown |
| Paid, parcel-level | [`apify-actor/`](apify-actor/) | agents on Apify | **$10/month rental** | structured JSON facts (Markdown optional) |

Humans use the Telegram bot. Autonomous **AI agents** that want a full,
parcel-level report either order and pay for it with the
[x402](https://docs.x402.org) protocol via the
[`x402-report-skill/`](x402-report-skill/) package, or rent the
[`apify-actor/`](apify-actor/) monthly. Both expose a **free coverage preview**
(`GET /api/agent/coverage` and `GET /api/partner/coverage`) so an agent can see
which chapters exist near a coordinate — and how many bytes/tokens each output
format would cost it — before paying. Use the free `city-insight` skill for
"which area is better?" questions; use a paid rail only when the user
authorises a paid, property-specific report.

### Choosing an output format

The paid rails default to **`format=json`**: per-chapter `verdict`, `band`,
`metrics` and `source`, plus a small top-level `summary` you can decide on in a
few hundred tokens. Prefer it over `markdown` unless a human will read the
result — the prose carries the same numbers at several times the token cost.
Base64 map images are **off by default** for the same reason.

