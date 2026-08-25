# Parcelabot city-insight MCP server

A minimal [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes one tool, `get_city_insight`, proxying the public Parcelabot
city-insight API. Works with any MCP client (Claude Desktop, etc.).

## Install & run

```bash
pip install -r requirements.txt
python server.py
```

## Configure Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "parcelabot": {
      "command": "python",
      "args": ["/absolute/path/to/ai-skills/mcp-server/server.py"],
      "env": { "PARCELABOT_BASE_URL": "https://parcelabot.duckdns.org" }
    }
  }
}
```

## Tool

`get_city_insight(location, pricing?)` → area-level Markdown for ONE location.

- `location` — place name (English) or `"lat,lng"`.
- `pricing` — optional `low` | `average` | `high`.

The output is **input data**, not a verdict. Call the tool twice to compare two
places. English only. If no report matches, the returned Markdown explains how
to generate a custom report.

Override the endpoint with `PARCELABOT_BASE_URL`.
