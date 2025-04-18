"""
MCP (Model Context Protocol) Server implementation
"""

import json
import logging
import uuid
from contextvars import ContextVar

from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.routing import Route, Mount

from agents.models.models import (
    MCPServer,
    MCPTool,
)
from agents.services.assistant_mcp_service import get_assistant_mcp_service
from agents.services.mcp_service import get_coin_api_mcp_service, _create_server_instance
from agents.services.open_service import verify_token_and_get_credentials
from agents.utils.session import get_async_session_ctx, get_user_from_request

logger = logging.getLogger(__name__)
ctx_correlation_id = ContextVar("correlation_id", default="")

transport = SseServerTransport("/messages/")

async def handle_coin_api_sse(request: Request):
    """Handle requests for the built-in coin-api service"""
    correlation_id = str(uuid.uuid4())
    ctx_correlation_id.set(correlation_id)
    logger.info(f"[{correlation_id}] Received coin-api service request: {request.method} {request.url.path}?{request.url.query}")
    
    try:
        # Extract user information from the request
        user = await get_user_from_request(request)
        
        # Create built-in coin-api MCP service instance
        mcp_service = get_coin_api_mcp_service(user)
        
        # Check request method
        async with transport.connect_sse(
                request.scope, request.receive, request._send
        ) as streams:
            await mcp_service.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name="coin-api",
                    server_version="0.1.0",
                    capabilities=mcp_service.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        
        logger.info(f"[{correlation_id}] coin-api service request processing completed")
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error occurred while processing coin-api request: {str(e)}")
        return Response(f"Error occurred while processing request: {str(e)}", status_code=500)

async def handle_assistant_api_sse(request: Request):
    """Handle requests for the assistant-api service"""
    correlation_id = str(uuid.uuid4())
    ctx_correlation_id.set(correlation_id)
    logger.info(f"[{correlation_id}] Received assistant-api service request: {request.method} {request.url.path}?{request.url.query}")
    user = {}
    try:
        access_key = request.query_params.get("api-key")
        if not access_key:
            return JSONResponse(
                {"error": "Missing API key"},
                status_code=401
            )

        try:
            async with get_async_session_ctx() as session:
                credentials = await verify_token_and_get_credentials(access_key, session)
                if not credentials:
                    return JSONResponse(
                        {"error": "Invalid API key"},
                        status_code=401
                    )

                user = credentials
                
                # Create assistant MCP service instance
                mcp_service = await get_assistant_mcp_service(user, session)
                
                # Connect SSE and process request
                async with transport.connect_sse(
                        request.scope, request.receive, request._send
                ) as streams:
                    try:
                        await mcp_service.run(
                            streams[0],
                            streams[1],
                            InitializationOptions(
                                server_name="assistant-api",
                                server_version="0.1.0",
                                capabilities=mcp_service.get_capabilities(
                                    notification_options=NotificationOptions(),
                                    experimental_capabilities={
                                        "user": user
                                    },
                                ),
                            ),
                        )
                    except Exception as e:
                        logger.error(f"[{correlation_id}] Error in assistant-api server run: {e}", exc_info=True)
                        # Send error message through SSE
                        await streams[1].send(json.dumps({"error": str(e)}))
                        raise
        except Exception as e:
            logger.error(f"[{correlation_id}] Error verifying API key: {e}", exc_info=True)
            return JSONResponse(
                {"error": "Error verifying API key"},
                status_code=500
            )
        
        logger.info(f"[{correlation_id}] assistant-api service request processing completed")
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error occurred while processing assistant-api request: {str(e)}")
        return Response(f"Error occurred while processing request: {str(e)}", status_code=500)

async def handle_dynamic_mcp(request: Request):
    """Handle requests for dynamically created MCP services"""
    correlation_id = str(uuid.uuid4())
    ctx_correlation_id.set(correlation_id)
    
    # Extract MCP service name from path
    mcp_name = request.path_params.get("mcp_name", "")
    logger.info(f"[{correlation_id}] Received dynamic MCP service request: {request.method} {request.url.path}?{request.url.query}")
    
    try:
        # Extract user information from the request
        user = await get_user_from_request(request)
            
        # Check if MCP service exists in the database
        async with get_async_session_ctx() as session:
            result = await session.execute(
                select(MCPServer)
                .options(selectinload(MCPServer.tools).selectinload(MCPTool.tool))
                .where(MCPServer.name == mcp_name)
            )
            server = result.scalar_one_or_none()
            
            if not server:
                logger.warning(f"[{correlation_id}] MCP service '{mcp_name}' not found")
                return JSONResponse(
                    {"error": f"MCP service '{mcp_name}' not found"},
                    status_code=404
                )

            # Create MCP server instance
            mcp_server = await _create_server_instance(mcp_name, user)

            # Connect SSE and process request
            async with transport.connect_sse(
                    request.scope, request.receive, request._send
            ) as streams:
                await mcp_server.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name=mcp_name,
                        server_version="0.1.0",
                        capabilities=mcp_server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        
        logger.info(f"[{correlation_id}] Dynamic MCP service '{mcp_name}' request processing completed")
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error occurred while processing dynamic MCP service '{mcp_name}' request: {str(e)}")
        return Response(f"Error occurred while processing request: {str(e)}", status_code=500)

async def handle_any_mcp(request: Request):
    """Route any MCP request to the appropriate handler"""
    # Extract MCP service name
    mcp_name = request.path_params.get("mcp_name", "")
    logger.info(f"handle_any_mcp {mcp_name}")
    
    # Choose handler based on MCP name
    if mcp_name == "coin-api":
        return await handle_coin_api_sse(request)
    elif mcp_name == "assistant-api":
        return await handle_assistant_api_sse(request)
    else:
        return await handle_dynamic_mcp(request)

async def handle_mcp_message(request: Request):
    """Handle MCP message requests"""
    correlation_id = str(uuid.uuid4())
    logger.debug(f"[{correlation_id}] Received MCP message request: {request.method} {request.url.path}?{request.url.query}")
    
    # Extract MCP service name from path
    parts = request.url.path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "mcp":
        mcp_name = parts[1]
        logger.debug(f"[{correlation_id}] Extracted MCP service name: {mcp_name}")

        if mcp_name == "coin-api":
            return await handle_coin_api_sse(request)
        elif mcp_name == "assistant-api":
            return await handle_assistant_api_sse(request)
        else:
            return await handle_dynamic_mcp(request)

    
    logger.warning(f"[{correlation_id}] Invalid MCP message path: {request.url.path}")
    return JSONResponse(
        {"error": "Invalid MCP message path"},
        status_code=404
    )

def get_all_routes():
    """Create all routes"""
    routes = [
        Route("/mcp/coin-api", endpoint=handle_coin_api_sse, methods=["GET"]),
        Route("/mcp/coin-api", endpoint=handle_coin_api_sse, methods=["POST"]),
        Route("/mcp/assistant-api", endpoint=handle_assistant_api_sse, methods=["GET", "POST"]),
        Route("/mcp/{mcp_name:path}", endpoint=handle_any_mcp, methods=["GET", "POST"]),
        Mount("/messages/", app=transport.handle_post_message),
    ]
    return routes

def get_application():
    """Create Starlette application"""
    routes = get_all_routes()
    return Starlette(routes=routes)

# Create application instance
application = get_application()
