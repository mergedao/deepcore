import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Body, Path, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.error_messages import get_error_message
from agents.common.response import RestResponse
from agents.exceptions import CustomAgentException, ErrorCode
from agents.middleware.auth_middleware import get_current_user
from agents.models.db import get_db
from agents.services import mcp_service

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateMCPServerRequest(BaseModel):
    """Create MCP Server Request"""
    mcp_name: str
    tool_ids: List[str]
    description: Optional[str] = None


class AddPromptTemplateRequest(BaseModel):
    """Add Prompt Template Request"""
    prompt_name: str
    description: str
    arguments: List[dict]
    template: str


class AddResourceRequest(BaseModel):
    """Add Resource Request"""
    resource_uri: str
    content: str
    mime_type: str = "text/plain"


@router.post("/mcp/create", summary="Create MCP Server")
async def create_mcp_server(
    request: CreateMCPServerRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Create an MCP server from tools
    
    Parameters:
    - **mcp_name**: MCP server name
    - **tool_ids**: List of tool IDs to expose as MCP interface
    - **description**: Optional MCP service description
    """
    try:
        result = await mcp_service.create_mcp_server_from_tools(
            mcp_name=request.mcp_name,
            tool_ids=request.tool_ids,
            user=user,
            session=session,
            description=request.description
        )
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error creating MCP server: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating MCP server: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.post("/mcp/{mcp_name}/prompts", summary="Add Prompt Template")
async def add_prompt_template(
    mcp_name: str = Path(..., description="MCP server name"),
    request: AddPromptTemplateRequest = Body(...),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Add a prompt template to an MCP server
    
    Parameters:
    - **mcp_name**: MCP server name
    - **prompt_name**: Prompt template name
    - **description**: Prompt description
    - **arguments**: List of prompt arguments
    - **template**: Prompt template text
    """
    try:
        result = await mcp_service.add_prompt_template(
            mcp_name=mcp_name,
            prompt_name=request.prompt_name,
            description=request.description,
            arguments=request.arguments,
            template=request.template,
            session=session
        )
        
        if not result:
            return RestResponse(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                msg=f"MCP server '{mcp_name}' not found"
            )
            
        return RestResponse(data={"success": True})
    except CustomAgentException as e:
        logger.error(f"Error adding prompt template: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error adding prompt template: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.post("/mcp/{mcp_name}/resources", summary="Add Resource")
async def add_resource(
    mcp_name: str = Path(..., description="MCP server name"),
    request: AddResourceRequest = Body(...),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Add a resource to an MCP server
    
    Parameters:
    - **mcp_name**: MCP server name
    - **resource_uri**: Resource URI
    - **content**: Resource content
    - **mime_type**: MIME type of the resource (default: text/plain)
    """
    try:
        result = await mcp_service.add_resource(
            mcp_name=mcp_name,
            resource_uri=request.resource_uri,
            content=request.content,
            mime_type=request.mime_type,
            session=session
        )
        
        if not result:
            return RestResponse(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                msg=f"MCP server '{mcp_name}' not found"
            )
            
        return RestResponse(data={"success": True})
    except CustomAgentException as e:
        logger.error(f"Error adding resource: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error adding resource: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/mcp/list", summary="List All MCP Servers")
async def list_mcp_servers(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    List all registered MCP servers
    """
    try:
        servers = await mcp_service.get_registered_mcp_servers(session)
        return RestResponse(data=servers)
    except CustomAgentException as e:
        logger.error(f"Error listing MCP servers: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing MCP servers: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.delete("/mcp/{mcp_name}", summary="Delete MCP Server")
async def delete_mcp_server(
    mcp_name: str = Path(..., description="MCP server name"),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Delete a specific MCP server
    
    Parameters:
    - **mcp_name**: Name of the MCP server to delete
    """
    try:
        result = await mcp_service.delete_mcp_server(mcp_name, session)
        if not result:
            return RestResponse(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                msg=f"MCP server '{mcp_name}' not found"
            )
        return RestResponse(data={"success": True})
    except CustomAgentException as e:
        logger.error(f"Error deleting MCP server: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting MCP server: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/mcp/tools/{tool_id}", summary="Get Tool MCP Service Info")
async def get_tool_mcp_info(
    tool_id: str = Path(..., description="Tool ID"),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get MCP service information for a specific tool
    
    Parameters:
    - **tool_id**: Tool ID
    """
    try:
        mapping = await mcp_service.get_tool_mcp_mapping(session)
        if tool_id not in mapping:
            return RestResponse(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                msg=f"Tool '{tool_id}' is not exposed as MCP"
            )
            
        mcp_name = mapping[tool_id]
        return RestResponse(data={
            "tool_id": tool_id,
            "mcp_name": mcp_name,
            "url": f"/mcp/{mcp_name}"
        })
    except CustomAgentException as e:
        logger.error(f"Error getting tool MCP info: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting tool MCP info: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        ) 