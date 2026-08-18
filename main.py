import logging

import typesense
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typesense.configuration import NodeConfigDict, ConfigDict
from typesense.types.document import SearchParameters

import uvicorn

from src.logger import RequestLoggingMiddleware, log_tool_errors, setup_logging


def unquote_env_value(value: str) -> str:
    """Strip whitespace and one layer of matching surrounding quotes.

    Env loaders disagree on quoting: python-dotenv (`uv run main.py`) and
    docker compose `env_file:` strip quotes, but `docker run --env-file` passes
    the line verbatim, so `KEY="value"` arrives with the quotes attached.
    """
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


class UnquotingEnvSource(EnvSettingsSource):
    """Env source that unquotes raw values before pydantic parses them."""

    def prepare_field_value(self, field_name, field, value, value_is_complex):
        if isinstance(value, str):
            value = unquote_env_value(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings, extra="ignore"):
    development: bool = False
    listen_host: str = "0.0.0.0"
    listen_port: int = 8000
    typesense_api_key: str = ""
    typesense_host: str = ""
    typesense_port: int = 8080
    typesense_protocol: str = "http"
    allowed_hosts: list[str] = []
    allowed_origins: list[str] = []
    log_dir: str = "logs"
    log_level: str = "INFO"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    log_to_console: bool = True

    model_config = SettingsConfigDict(env_file=".env")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            UnquotingEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("typesense_protocol")
    @classmethod
    def validate_protocol(cls, value: str) -> str:
        if value not in {"http", "https"}:
            raise ValueError(
                f"TYPESENSE_PROTOCOL must be 'http' or 'https', got {value!r}"
            )
        return value

    @model_validator(mode="after")
    def validate_required(self) -> "Settings":
        missing = [
            name
            for name, value in (
                ("TYPESENSE_API_KEY", self.typesense_api_key),
                ("TYPESENSE_HOST", self.typesense_host),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")
        return self


settings = Settings()

setup_logging(
    log_dir=settings.log_dir,
    level=settings.log_level,
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count,
    console=settings.log_to_console,
)

logger = logging.getLogger("hbg.main")

mcp = FastMCP(
    "HBG Typesense MCP",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
    ),
)

typesense_client = typesense.Client(
    ConfigDict(
        api_key=settings.typesense_api_key,
        nodes=[
            NodeConfigDict(
                host=settings.typesense_host,
                port=settings.typesense_port,
                protocol=settings.typesense_protocol,
            )
        ],
    )
)


@mcp.tool()
@log_tool_errors
async def list_collections():
    """List available Typesense collections with compact metadata.

    Use when:
        - You need to discover which collections exist.
        - You need a lightweight overview before selecting a collection.

    Do not use when:
        - You need full schema and settings for one collection
          (use get_collection_info).
        - You need document-level search results (use search).

    Returns:
        list[dict]: One item per collection with:
            - name (str): Collection name.
            - num_documents (int): Number of indexed documents.
            - fields (list[dict]): Field summaries with name and type.

    Notes:
        - This tool returns a trimmed subset of collection metadata.
    """
    collections = typesense_client.collections.retrieve()

    trimmed = [
        {
            "name": col["name"],
            "num_documents": col["num_documents"],
            "fields": [
                {"name": field["name"], "type": field["type"]}
                for field in col["fields"]
            ],
        }
        for col in collections
    ]

    return trimmed


@mcp.tool()
@log_tool_errors
async def get_collection_info(collection_name: str):
    """Get full schema and metadata for a single Typesense collection.

    Use when:
        - You need complete collection details (fields, defaults, settings).
        - You need to verify a collection exists before querying.

    Do not use when:
        - You only need an overview of all collections (use list_collections).
        - You need matching documents for a user query (use search).

    Args:
        collection_name (str): Exact name of the collection to describe.

    Returns:
        dict: Full collection metadata returned by Typesense.

    Raises:
        typesense.exceptions.ObjectNotFound: If the collection does not exist.
    """
    collection = typesense_client.collections[collection_name].retrieve()
    return collection


@mcp.tool()
@log_tool_errors
async def search(collection_name: str, query: str):
    """Search documents in a Typesense collection using free-text query.

    Use when:
        - The user asks to find relevant documents by keywords.
        - You already know the target collection name.

    Do not use when:
        - You need collection discovery (use list_collections).
        - You need full collection schema/metadata (use get_collection_info).

    Args:
        collection_name (str): Exact name of the collection to search.
        query (str): User search text.

    Returns:
        dict: Typesense search response containing hits and metadata.

    Notes:
        - Searches the fields: post_title, content.
        - If no matches are found, returns a valid response with empty hits.
    """
    results = typesense_client.collections[collection_name].documents.search(
        SearchParameters(q=query, query_by="post_title,content")
    )
    return results


app = RequestLoggingMiddleware(mcp.streamable_http_app())

if __name__ == "__main__":
    logger.info(
        "Starting HBG Typesense MCP on %s:%s", settings.listen_host, settings.listen_port)
    logger.info(
        "Typesense node: %r", f"{settings.typesense_protocol}://{settings.typesense_host}:{settings.typesense_port}")
    logger.info("Dev mode: %s", settings.development)
    logger.info("Key: %s", settings.typesense_api_key[0:4] + "..." + settings.typesense_api_key[-4:] if settings.typesense_api_key else "(none)")
    uvicorn.run(
        'main:app',
        host=settings.listen_host,
        port=settings.listen_port,
        reload=settings.development,
        # Keep the root logger config from setup_logging; the middleware above
        # is the single source of request logs.
        log_config=None,
        access_log=False,
    )
