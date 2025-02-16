import datetime
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from agents.agent.factory.gen_agent import gen_agent
from agents.common.response import RestResponse
from agents.models.db import get_db
from agents.protocol.schemas import AgentDTO, DialogueResponse, DialogueRequest, AgentStatus, \
    PaginationParams, AgentMode, AICreateAgentDTO
from agents.services import agent_service

router = APIRouter()

defaults = {
    'id': uuid.uuid4().hex,
    'create_time': datetime.datetime.now(),
    'update_time': datetime.datetime.now(),
    'mode': AgentMode.REACT,
    'status': AgentStatus.ACTIVE,
    'max_loops': 3,
    'name': "",
    'description': "",
    'icon': "",
    'role_settings': "",
    'welcome_message': "",
    'twitter_link': "",
    'telegram_bot_id': "",
    'tool_prompt': "",
    'tools': []
}


@router.post("/agents/create", summary="创建 Agent")
async def create_agent(agent: AgentDTO, session: AsyncSession = Depends(get_db)):
    """
    Create a new agent.
    """
    for key, value in defaults.items():
        if getattr(agent, key) is None:
            setattr(agent, key, value)

    agent = await agent_service.create_agent(
        agent,
        session
    )
    return RestResponse(data=agent)


@router.get("/agents/list", summary="获取 Agent 列表")
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
    agents = await agent_service.list_agents(status=status, skip=pagination.skip, limit=pagination.limit,
                                             session=session)
    return RestResponse(data=agents)


@router.get("/agents/get", summary="获取 Agent 详情")
async def get_agent(
        agent_id: str = Query(None, description="agent id"),
        session: AsyncSession = Depends(get_db)
):
    agents = await agent_service.get_agent(agent_id, session=session)
    return RestResponse(data=agents)


@router.post("/agents/update", summary="更新 Agent")
async def update_agent(agent: AgentDTO, session: AsyncSession = Depends(get_db)):
    """
    Update an existing agent."""
    agent = await agent_service.update_agent(
        agent,
        session=session
    )
    return RestResponse(data=agent)


@router.delete("/agents/delete", summary="删除 Agent")
async def delete_agent(agent_id: str = Query(None, description="agent id"), session: AsyncSession = Depends(get_db)):
    """
    Delete an agent by setting its is_deleted flag to True.
    
    - **agent_id**: ID of the agent to delete
    """
    await agent_service.delete_agent(agent_id, session)
    return RestResponse(data="ok")

@router.post("/agents/ai/create", summary="AI 创建 Agent")
async def ai_create_agent(agent: AICreateAgentDTO, session: AsyncSession = Depends(get_db)):
    """
    Create a new agent.
    """
    resp = gen_agent(agent.description)
    return StreamingResponse(content=resp, media_type="text/event-stream")


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


@router.get("/agents/{agent_id}/dialogue", response_model=DialogueResponse)
async def dialogue_get(
        agent_id: int,
        query: Optional[str] = Query(None, description="Query message from the user"),
        conversation_id: Optional[str] = Query(
            None,
            alias="conversationId",
            description="ID of the conversation"
        ),
        session: AsyncSession = Depends(get_db)
):
    """
    Handle a dialogue between a user and an agent using GET method.

    - **agent_id**: ID of the agent to interact with
    - **query**: Query message from the user (optional)
    - **conversation_id**: ID of the conversation (optional, auto-generated if not provided)
    """
    request = DialogueRequest(query=query, conversation_id=conversation_id)
    resp = agent_service.dialogue(agent_id, request, session)
    return StreamingResponse(content=resp, media_type="text/event-stream")