from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from agents.common.response import RestResponse
from agents.middleware.auth_middleware import get_current_user
from agents.models.db import get_db
from agents.protocol.response import ToolModel
from agents.protocol.schemas import ToolCreate, ToolUpdate, AgentToolsRequest
from agents.services import tool_service

router = APIRouter()


@router.post("/tools/create", summary="Create Tool", response_model=RestResponse[ToolModel])
async def create_tool(
        tool: ToolCreate,
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Create a new tool
    
    Parameters:
    - **name**: Name of the tool
    - **type**: Type of the tool (openapi or function)
    - **content**: Content or configuration of the tool
    - **auth_config**: Optional authentication configuration
    """
    tool = await tool_service.create_tool(
        tool.name,
        tool.type,
        tool.content,
        user,
        session,
        tool.auth_config
    )
    return RestResponse(data=tool)


@router.get("/tools/list", summary="List Tools")
async def list_tools(
        include_public: bool = Query(True, description="Include public tools"),
        only_official: bool = Query(False, description="Show only official tools"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    List all available tools
    """
    tools = await tool_service.get_tools(
        user=user,
        include_public=include_public,
        only_official=only_official,
        session=session
    )
    return RestResponse(data=tools)


@router.get("/tools/{tool_id}", summary="Get Tool Details")
async def get_tool(
        tool_id: str,
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Retrieve a tool's information by its ID.
    
    - **tool_id**: UUID of the tool to retrieve
    """
    return RestResponse(data=await tool_service.get_tool(tool_id, user, session))


@router.put("/tools/{tool_id}", summary="Update Tool")
async def update_tool(
        tool_id: int, 
        tool: ToolUpdate, 
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Update an existing tool
    
    - **tool_id**: ID of the tool to update
    - **type**: New type of the tool
    - **content**: New content of the tool
    """
    tool = await tool_service.update_tool(
        tool_id, 
        tool.name, 
        tool.type, 
        tool.content,
        user,
        session
    )
    return RestResponse(data=tool)


@router.delete("/tools/{tool_id}", summary="Delete Tool")
async def delete_tool(
        tool_id: int, 
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Delete a tool by setting its is_deleted flag to True.
    
    - **tool_id**: ID of the tool to delete
    """
    await tool_service.delete_tool(tool_id, user, session)
    return RestResponse(data="ok")


@router.post("/tools/{tool_id}/publish", summary="Publish Tool")
async def publish_tool(
        tool_id: str,
        is_public: bool = Query(True, description="Set tool as public"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Publish or unpublish a tool
    """
    await tool_service.publish_tool(tool_id, is_public, user, session)
    return RestResponse(data="ok")


@router.post("/agents/{agent_id}/tools", summary="Assign Tools to Agent")
async def assign_tools(
        agent_id: str = Path(..., description="ID of the agent"),
        request: AgentToolsRequest = Body(..., description="Tool IDs to assign"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Assign multiple tools to an agent
    
    Parameters:
    - **agent_id**: ID of the agent
    - **tool_ids**: List of tool IDs to assign
    """
    await tool_service.assign_tools_to_agent(request.tool_ids, agent_id, user, session)
    return RestResponse(data="ok")


@router.delete("/agents/{agent_id}/tools", summary="Remove Tools from Agent")
async def remove_tools(
        agent_id: str,
        request: AgentToolsRequest,
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Remove multiple tools from an agent
    
    - **agent_id**: ID of the agent
    - **tool_ids**: List of tool IDs to remove
    """
    await tool_service.remove_tools_from_agent(request.tool_ids, agent_id, user, session)
    return RestResponse(data="ok")


@router.get("/agents/{agent_id}/tools", summary="Get Agent Tools")
async def get_agent_tools(
        agent_id: str,
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Get all tools associated with a specific agent
    """
    tools = await tool_service.get_tools_by_agent(
        agent_id=agent_id,
        user=user,
        session=session
    )
    return RestResponse(data=tools)
