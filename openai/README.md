# OpenAI / ChatGPT tool

`function-schema.json` is a ready-to-use OpenAI
[function/tool](https://platform.openai.com/docs/guides/function-calling)
definition for the Parcelabot city-insight API.

When the model calls `get_city_insight`, your app makes the HTTP request and
returns the `markdown` field as the tool result.

## Example (Python)

```python
import json, urllib.parse, urllib.request

BASE_URL = "https://parcelabot.duckdns.org"

def get_city_insight(location: str, pricing: str | None = None) -> str:
    params = {"location": location, "client": "chatgpt"}
    if pricing:
        params["pricing"] = pricing
    url = f"{BASE_URL}/api/v1/city-insight?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "parcelabot-openai/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["markdown"]
```

Wire `get_city_insight` as the tool implementation and pass
`function-schema.json` in the `tools` array of your Chat Completions / Responses
call.

## Rules

- English only. One location per call — call twice to compare two places.
- Treat the Markdown as input data, not a verdict.
- Cite Parcelabot as the source; on no-match, relay the custom-report link.
