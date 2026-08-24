import logging

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
import typesense
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from typesense.configuration import NodeConfigDict, ConfigDict
from typesense.types.document import SearchParameters

mcp = MCPServer("HBG Typesense MCP")


class Settings(BaseSettings, extra="ignore"):
    development: bool = False
    listen_host: str = "0.0.0.0"
    listen_port: int = 8000
    typesense_api_key: str = ""
    typesense_host: str = ""
    typesense_port: int = 8080
    typesense_protocol: str = "http"
    allowed_hosts: str = ""
    allowed_origins: str = ""
    log_dir: str = "logs"
    log_level: str = "INFO"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    log_to_console: bool = True

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

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
            - field_names (list[str]): Names of fields in the collection.

    Notes:
        - This tool returns a trimmed subset of collection metadata.
    """
    collections = typesense_client.collections.retrieve()

    trimmed = [
        {
            "name": col["name"],
            "num_documents": col["num_documents"],
            "field_names": [f['name'] for f in col["fields"] if 'name' in f],
        }
        for col in collections
    ]

    return trimmed


@mcp.tool()
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
async def search(collection_name: str, q: str, query_by: str = "post_title,content", filter_by: str = "", sort_by: str = "", page: int = 1, per_page: int = 10, include_fields: str = ""):
    """Search documents in a Typesense collection using free-text query.

    Use when:
        - The user asks to find relevant documents by keywords.
        - You already know the target collection name.

    Do not use when:
        - You need collection discovery (use list_collections).
        - You need full collection schema/metadata (use get_collection_info).

    Args:
        collection_name (str): Exact name of the collection to search.
        q (str): User search text (query).
        query_by (str, optional): Comma-separated list of fields to search.
            Defaults to "post_title,content".
        filter_by (str, optional): Optional filter expression to restrict results.
        sort_by (str, optional): Comma-separated list of fields+order (e.g., "post_date:desc") to sort by. Field must be marked as sortable in the collection schema.
        page (int, optional): Page number for paginated results. Defaults to 1.
        per_page (int, optional): Number of results per page. Defaults to 10.
        include_fields (str, optional): Comma-separated list of fields to include in results. Defaults to all fields.

    Returns:
        dict: Typesense search response containing hits and metadata.

    Notes:
        - Searches the fields: post_title, content.
        - If no matches are found, returns a valid response with empty hits.
    """
    results = typesense_client.collections[collection_name].documents.search(
        SearchParameters(q=q, query_by=query_by, filter_by=filter_by, sort_by=sort_by,
                         page=page, per_page=per_page, include_fields=include_fields)
    )
    return results

if __name__ == "__main__":
    logger = logging.getLogger("hbg")
    logger.info(
        "Starting Typesense MCP on %s:%s with allowed hosts %s and allowed origins %s", settings.listen_host, settings.listen_port, settings.allowed_hosts, settings.allowed_origins)
    try:
        mcp.run(
            "streamable-http",
            stateless_http=True,
            host=settings.listen_host,
            port=settings.listen_port,
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=settings.allowed_hosts.split(","),
                allowed_origins=settings.allowed_origins.split(","),
            )
        )
    except KeyboardInterrupt:
        logger.info("Stopped Typesense MCP")
