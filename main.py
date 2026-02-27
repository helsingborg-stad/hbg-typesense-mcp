import typesense
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic_settings import BaseSettings, SettingsConfigDict
from typesense.configuration import NodeConfigDict, ConfigDict
from typesense.types.document import SearchParameters

import uvicorn


class Settings(BaseSettings):
    development: bool = False
    listen_host: str = "0.0.0.0"
    listen_port: int = 8005
    typesense_api_key: str
    typesense_host: str
    typesense_port: int = 8080
    typesense_protocol: str = 'http'
    typesense_collection: str
    allowed_hosts: list[str] = []
    allowed_origins: list[str] = []

    model_config = SettingsConfigDict(env_file='.env')


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


app = mcp.streamable_http_app()

if __name__ == "__main__":
    uvicorn.run(app, host=settings.listen_host, port=settings.listen_port, reload=settings.development)
