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
docker run -p 8000:8000 -e TYPESENSE_API_KEY=xxx -e TYPESENSE_HOST=xxx -e TYPESENSE_COLLECTION=xxx hbg-typesense-mcp

# Docker Compose (Traefik + Let's Encrypt)
# Set DOMAIN and ACME_EMAIL in .env first
docker compose up --build -d
docker compose logs -f
docker compose down
```

## Architecture

All application logic lives in `main.py`:
- **Settings** — `pydantic-settings` `BaseSettings` class loading from `.env` file. Required: `typesense_api_key`, `typesense_host`, `typesense_collection`.
- **MCP server** — `FastMCP` configured for stateless HTTP with JSON responses and DNS rebinding protection. Configurable `allowed_hosts`/`allowed_origins`.
- **Typesense client** — Initialized from settings, searches the configured collection across `post_title` and `content` fields.
- **ASGI app** — `mcp.streamable_http_app()` served by uvicorn directly.

## Environment Variables

See `.env.example` for all available variables. Copy to `.env` and fill in required values. `ALLOWED_HOSTS` and `ALLOWED_ORIGINS` are JSON-formatted lists.

## Conventions

- Python 3.11+, managed with `uv`
- Commit messages use emoji prefixes (e.g. `✨ Feat:`, `🎉 Init:`)
