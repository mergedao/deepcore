from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount

from agents.agent.mcp import coin_api_mcp


def sse_app() -> Starlette:
    """Return an instance of the SSE server app."""
    sse = SseServerTransport("/messages/")

    async def handle_coin_sse(request):
        async with sse.connect_sse(
                request.scope, request.receive, request._send
        ) as streams:
            await coin_api_mcp.server.server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name="coin-api",
                    server_version="0.1.0",
                    capabilities=coin_api_mcp.server.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    return Starlette(
        # debug=self.settings.debug,
        routes=[
            Route("/mcp/coin-api", endpoint=handle_coin_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

def get_all_routers() -> Starlette:

    return sse_app()
