#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Assistant API MCP Server Module

This module implements an MCP server that exposes the assistant dialogue API via the Model Calling Protocol.
It provides tools for interacting with intelligent assistants through a standardized MCP interface.
"""

import json
import logging
from typing import Dict, List, Any, AsyncGenerator

import httpx
from mcp.server import Server
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.config import SETTINGS
from agents.protocol.schemas import DialogueRequest
from agents.services import agent_service

logger = logging.getLogger(__name__)

# Create server instance
server = Server("assistant-api")


@server.list_tools()
async def handle_list_tools() -> List[Dict[str, Any]]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        {
            "name": "chat-with-agent",
            "description": "Engage in a conversation with a specified intelligent assistant",
            "is_stream": True,
            "parameters": {
                "agent_id": {
                    "type": "string",
                    "description": "ID of the agent to chat with"
                },
                "message": {
                    "type": "string",
                    "description": "Message from the user to the assistant"
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Optional conversation ID to continue a previous dialogue",
                    "required": False
                },
                "init_flag": {
                    "type": "boolean",
                    "description": "Whether this is an initialization dialogue",
                    "default": False
                }
            }
        },
        {
            "name": "list-available-agents",
            "description": "List all available intelligent assistants",
            "is_stream": False,
            "parameters": {
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination",
                    "default": 1,
                    "minimum": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of items per page",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                }
            }
        }
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any] = None
) -> List[Dict[str, Any]] | AsyncGenerator[str, None]:
    """
    Handle tool execution requests.
    
    Currently supported tools:
    - chat-with-agent: Engage in a conversation with a specified intelligent assistant
    - list-available-agents: List all available intelligent assistants
    """
    # Create a database session function to ensure we don't encounter exceptions in test environments
    async def get_session() -> AsyncSession:
        from agents.models.db import SessionLocal
        async with SessionLocal() as session:
            yield session
    
    if name == "chat-with-agent":
        if not arguments:
            return [{"error": "Missing parameters"}]
        
        agent_id = arguments.get("agent_id")
        message = arguments.get("message")
        conversation_id = arguments.get("conversation_id")
        init_flag = arguments.get("init_flag", False)
        
        if not agent_id:
            return [{"error": "Missing agent_id parameter"}]
        
        if not message:
            return [{"error": "Missing message parameter"}]
        
        # Construct dialogue request
        dialogue_request = DialogueRequest(
            query=message,
            conversationId=conversation_id,
            initFlag=init_flag
        )
        
        # Create database session
        session_gen = get_session()
        session = await session_gen.__anext__()
        
        try:
            # Call the existing dialogue service
            response_stream = agent_service.dialogue(agent_id, dialogue_request, None, session)
            
            # Convert service response to MCP-compatible format
            async def adapted_stream():
                async for chunk in response_stream:
                    try:
                        if chunk.startswith("data: "):
                            content = chunk[6:]  # Remove "data: " prefix
                            if content != "[DONE]":
                                yield content
                    except Exception as e:
                        logger.error(f"Error processing response stream: {e}")
                        yield json.dumps({"error": f"Error processing response stream: {str(e)}"})
                        break
                        
            return adapted_stream()
        except Exception as e:
            logger.error(f"Error calling dialogue service: {e}")
            return [{"error": f"Error calling dialogue service: {str(e)}"}]
        finally:
            # Close session
            await session.close()
    
    elif name == "list-available-agents":
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 10)
        
        try:
            # Execute API call using the base URL
            base_url = SETTINGS.API_BASE_URL or "http://localhost:8080"
            url = f"{base_url}/api/agents/public?page={page}&page_size={page_size}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                result = response.json()
                
                # Extract agent data
                if "data" in result and isinstance(result["data"], dict) and "items" in result["data"]:
                    agents = result["data"]["items"]
                    
                    # Return simplified list
                    return [{"agents": agents}]
                else:
                    return [{"error": "Unexpected API response format", "details": result}]
                    
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return [{"error": f"Error listing agents: {str(e)}"}]
            
    else:
        return [{"error": f"Unknown tool: {name}"}] 