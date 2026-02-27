import typesense
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic_settings import BaseSettings, SettingsConfigDict
from typesense.configuration import NodeConfigDict, ConfigDict
from typesense.types.document import SearchParameters


class Settings(BaseSettings):
    development: bool = False
    typesense_api_key: str
    typesense_host: str
    typesense_port: int = 8080
    typesense_protocol: str = 'http'
    typesense_collection: str

    model_config = SettingsConfigDict(env_file='.env')


settings = Settings()

mcp = FastMCP(
    "HBG Typesense MCP",
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            "host.docker.internal:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            "http://host.docker.internal:*",
        ],
    ) if settings.development else None,
)

typesense_client = typesense.Client(ConfigDict(
    api_key=settings.typesense_api_key,
    nodes=[NodeConfigDict(
        host=settings.typesense_host,
        port=settings.typesense_port,
        protocol=settings.typesense_protocol
    )]
))


@mcp.tool()
async def search(query: str):
    """Search Typesense for results.

    Args:
        query (str): The search query.
    """
    results = typesense_client.collections[settings.typesense_collection].documents.search(SearchParameters(
        q=query,
        query_by='post_title,content'
    ))
    return results


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
