# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Minimal MCP (Model Context Protocol) server that wraps Typesense search. Single-file Python app (`main.py`) exposing one `search` tool over stateless HTTP using the MCP SDK.

## Commands

```bash
# Install dependencies
uv sync --frozen

# Run the server
uv run main.py

# Run with hot reload (development mode)
DEVELOPMENT=true uv run main.py

# Docker
docker build -t hbg-typesense-mcp .
docker run -p 8000:8000 -e TYPESENSE_API_KEY=xxx -e TYPESENSE_HOST=xxx hbg-typesense-mcp

# Docker Compose (Traefik + Let's Encrypt)
# Set DOMAIN and ACME_EMAIL in .env first
docker compose up --build -d
docker compose logs -f
docker compose down
```

## Architecture

Tool and server wiring lives in `main.py`, logging in `src/logger/`:
- **Settings** — `pydantic-settings` `BaseSettings` class loading from `.env` file. Required: `typesense_api_key`, `typesense_host`.
- **MCP server** — `FastMCP` configured for stateless HTTP with JSON responses and DNS rebinding protection. Configurable `allowed_hosts`/`allowed_origins`.
- **Typesense client** — Initialized from settings, searches the configured collection across `post_title` and `content` fields.
- **ASGI app** — `mcp.streamable_http_app()` wrapped in `RequestLoggingMiddleware`, served by uvicorn directly.

## Logging

`setup_logging()` (from `src/logger/setup.py`) configures the root logger at import time in `main.py`, so it also applies under `--reload` and to library loggers (uvicorn, mcp). Timestamps are ISO 8601 in UTC. Handlers, all writing to `LOG_DIR` (default `logs/`, gitignored):
- **`app.log`** — `RotatingFileHandler`, everything *below* ERROR (filtered by `BelowErrorFilter`).
- **`error.log`** — plain `FileHandler`, ERROR and above with full tracebacks.
- **stderr** — same formatter, disable with `LOG_TO_CONSOLE=false`.

`uvicorn.run()` is called with `log_config=None` and `access_log=False`; `RequestLoggingMiddleware` is the single source of request logs (`METHOD /path <status> <ms> client=<ip>`, at ERROR for 5xx and unhandled exceptions).

Every `@mcp.tool()` function must also be decorated with `@log_tool_errors` (applied *below* `@mcp.tool()`). FastMCP converts tool exceptions into an error result over HTTP 200, so without it failures never reach `error.log`.

## Environment Variables

See `.env.example` for all available variables. Copy to `.env` and fill in required values. `ALLOWED_HOSTS` and `ALLOWED_ORIGINS` are JSON-formatted lists.

## Conventions

- Python 3.11+, managed with `uv`
- Commit messages use emoji prefixes (e.g. `✨ Feat:`, `🎉 Init:`)
