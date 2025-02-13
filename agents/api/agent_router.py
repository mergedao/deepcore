from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, AsyncIterator

from starlette.responses import StreamingResponse

from agents.common.response import RestResponse
from agents.models.db import get_db
from agents.protocol.schemas import AgentCreate, AgentUpdate, DialogueResponse, DialogueRequest, AgentStatus, PaginationParams
from agents.services import agent_service

router = APIRouter()

@router.post("/agents/create")
async def create_agent(agent: AgentCreate, session: AsyncSession = Depends(get_db)):
    """
    Create a new agent.
    
    - **name**: Name of the agent
    - **description**: Description of the agent
    - **mode**: Mode of the agent, default is 'ReAct'
    - **icon**: Icon of the agent
    - **status**: Status of the agent
    - **tool_prompt**: Tool prompt for the agent
    - **max_loops**: Maximum loops for the agent, default is 5
    - **tenant_id**: Tenant ID for the agent
    """
    agent = await agent_service.create_agent(
        agent.name,
        agent.description,
        agent.mode,
        agent.icon,
        agent.status,
        agent.tool_prompt,
        agent.max_loops,
        agent.tools,
        session
    )
    return RestResponse(data=agent)

@router.get("/agents/get")
async def list_agents(
    status: Optional[AgentStatus] = Query(None, description="Filter agents by status"),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of agents with pagination, optionally filtered by status.
    
    - **status**: Filter agents by their status (active, inactive, or draft)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    agents = await agent_service.list_agents(status=status, skip=pagination.skip, limit=pagination.limit, session=session)
    return RestResponse(data=agents)

@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, agent: AgentUpdate, session: AsyncSession = Depends(get_db)):
    """
    Update an existing agent.
    
    - **agent_id**: ID of the agent to update
    - **name**: New name of the agent
    - **description**: New description of the agent
    - **status**: New status of the agent
    - **tool_prompt**: New tool prompt for the agent
    - **max_loops**: New maximum loops for the agent
    - **tools**: New tools for the agent
    """
    agent = await agent_service.update_agent(
        agent_id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        tool_prompt=agent.tool_prompt,
        max_loops=agent.max_loops,
        tools=agent.tools,
        session=session
    )
    return RestResponse(data=agent)

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: int, session: AsyncSession = Depends(get_db)):
    """
    Delete an agent by setting its is_deleted flag to True.
    
    - **agent_id**: ID of the agent to delete
    """
    await agent_service.delete_agent(agent_id, session)
    return RestResponse(data="ok")

@router.post("/agents/{agent_id}/dialogue", response_model=DialogueResponse)
async def dialogue(agent_id: int, request: DialogueRequest,
             session: AsyncSession = Depends(get_db)):
    """
    Handle a dialogue between a user and an agent.
    
    - **agent_id**: ID of the agent to interact with
    - **user_id**: ID of the user
    - **message**: Message from the user
    """
    # Placeholder logic for generating a response
    resp = agent_service.dialogue(agent_id, request, session)
    return StreamingResponse(content=resp, media_type="text/event-stream")
