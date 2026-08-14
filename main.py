import typesense
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic_settings import BaseSettings, SettingsConfigDict
from typesense.configuration import NodeConfigDict, ConfigDict
from typesense.types.document import SearchParameters

import uvicorn


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

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

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


app = mcp.streamable_http_app()

if __name__ == "__main__":
    print(
        f"Starting HBG Typesense MCP on {settings.listen_host}:{settings.listen_port}")
    print(
        f"Typesense host: {settings.typesense_host}:{settings.typesense_port} ({settings.typesense_protocol})")
    print(f"Dev mode: {settings.development}")
    uvicorn.run(
        'main:app',
        host=settings.listen_host,
        port=settings.listen_port,
        reload=settings.development,
    )
