# HBG Typesense MCP server

Minimal implementation MCP server for basic search in Typesense.

## Tests

Run all tests from the project root:

```bash
uv run pytest
```

uv installs the development dependencies automatically. Tests use a fake
Typesense client and do not require a running Typesense server or API credentials.
