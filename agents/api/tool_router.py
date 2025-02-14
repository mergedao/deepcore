from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.response import RestResponse
from agents.models.db import get_db
from agents.protocol.schemas import ToolCreate, ToolUpdate
from agents.services import tool_service

router = APIRouter()


@router.post("/tools/create")
async def create_tool(tool: ToolCreate, session: AsyncSession = Depends(get_db)):
    """
    Create a new tool and associate it with an agent.
    
    - **app_id**: ID of the agent to associate the tool with
    - **type**: Type of the tool
    - **content**: Content of the tool
    """
    tool = await tool_service.create_tool(tool.app_id, tool.name, tool.type, tool.content, session)
    return RestResponse(data=tool)


@router.put("/tools/{tool_id}")
async def update_tool(tool_id: int, tool: ToolUpdate, session: AsyncSession = Depends(get_db)):
    """
    Update an existing tool.
    
    - **tool_id**: ID of the tool to update
    - **type**: New type of the tool
    - **content**: New content of the tool
    """
    tool = await tool_service.update_tool(tool_id, tool.name, tool.type, tool.content, session)
    return RestResponse(data=tool)


@router.delete("/tools/{tool_id}")
async def delete_tool(tool_id: int, session: AsyncSession = Depends(get_db)):
    """
    Delete a tool by setting its is_deleted flag to True.
    
    - **tool_id**: ID of the tool to delete
    """
    await tool_service.delete_tool(tool_id, session)
    return RestResponse(data="ok")


@router.get("/tools/{tool_id}")
async def get_tool(tool_id: int, session: AsyncSession = Depends(get_db)):
    """
    Retrieve a tool's information by its ID.
    
    - **tool_id**: ID of the tool to retrieve
    """
    return RestResponse(data=await tool_service.get_tool(tool_id, session))
