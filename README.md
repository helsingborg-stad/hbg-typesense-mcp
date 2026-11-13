# HBG Typesense MCP server

Minimal implementation MCP server for basic search in Typesense.

## Tests

Run all tests from the project root:

```bash
uv run pytest
```

uv installs the development dependencies automatically. Tests use a fake
Typesense client and do not require a running Typesense server or API credentials.

## Publishing the Docker image

In GitHub Actions, run **Publish Docker image** manually and select the branch
or tag to build. The workflow publishes the selected revision to
`ghcr.io/helsingborg-stad/hbg-typesense-mcp`, tagged with the selected branch
or tag name. Characters that are invalid in Docker tags, such as `/`, are
replaced with `-`; names that normalize to the same tag will overwrite it.
The workflow does not automatically publish a `latest` tag.

The workflow uses `GITHUB_TOKEN` with permission to write packages. Package
visibility and access can be managed in the GitHub Container Registry settings.
