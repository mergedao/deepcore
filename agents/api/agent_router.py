import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from agents.agent.factory.gen_agent import gen_agent
from agents.common.response import RestResponse
from agents.middleware.auth_middleware import get_current_user, get_optional_current_user
from agents.models.db import get_db
from agents.protocol.schemas import AgentDTO, DialogueResponse, DialogueRequest, AgentStatus, \
    PaginationParams, AgentMode
from agents.services import agent_service
from agents.exceptions import CustomAgentException, ErrorCode
from agents.common.error_messages import get_error_message

router = APIRouter()
logger = logging.getLogger(__name__)

defaults = {
    'id': uuid.uuid4().hex,
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
    'tools': [],
    'suggested_questions': [],
}


@router.post("/agents/create", summary="Create Agent", response_model=RestResponse[AgentDTO])
async def create_agent(
        agent: AgentDTO = Body(..., description="Agent configuration data"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Create a new agent

    Parameters:
    - **name**: Name of the agent
    - **description**: Description of the agent
    - **mode**: Mode of the agent (ReAct or call)
    - **tools**: Optional list of tools to associate
    - **model_id**: Optional ID of the model to use
    - **suggested_questions**: Optional list of suggested questions
    """
    try:
        logger.info(f"Creating agent with data: {agent.model_dump()}")
        
        # Set default values for missing fields
        for key, value in defaults.items():
            if getattr(agent, key) is None:
                setattr(agent, key, value)

        # Generate new UUID for the agent
        agent.id = str(uuid.uuid4())
        
        # Create agent
        result = await agent_service.create_agent(agent, user, session)
        logger.info(f"Agent created successfully with ID: {result.id}")
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error in agent creation: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in agent creation: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/agents/list", summary="List Personal Agents")
async def list_personal_agents(
        status: Optional[AgentStatus] = Query(None, description="Filter agents by status"),
        include_public: bool = Query(False, description="Include public agents along with personal agents"),
        category_id: Optional[int] = Query(None, description="Filter agents by category"),
        pagination: PaginationParams = Depends(),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of user's personal agents with pagination.

    - **status**: Filter agents by their status (active, inactive, or draft)
    - **include_public**: Whether to include public agents along with personal agents
    - **category_id**: Optional filter for category ID
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (1-100)
    """
    try:
        # Calculate offset from page number
        offset = (pagination.page - 1) * pagination.page_size

        agents = await agent_service.list_personal_agents(
            status=status,
            skip=offset,
            limit=pagination.page_size,
            user=user,
            include_public=include_public,
            category_id=category_id,
            session=session
        )
        return RestResponse(data=agents)
    except CustomAgentException as e:
        logger.error(f"Error listing personal agents: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing personal agents: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/agents/public", summary="List Public Agents")
async def list_public_agents(
        status: Optional[AgentStatus] = Query(None, description="Filter agents by status"),
        only_official: bool = Query(False, description="Show only official agents"),
        only_hot: bool = Query(False, description="Show only hot agents"),
        category_id: Optional[int] = Query(None, description="Filter agents by category"),
        pagination: PaginationParams = Depends(),
        session: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of public or official agents with pagination.

    - **status**: Filter agents by their status (active, inactive, or draft)
    - **only_official**: Whether to show only official agents
    - **only_hot**: Whether to show only hot agents
    - **category_id**: Optional filter for category ID
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (1-100)
    """
    try:
        # Calculate offset from page number
        offset = (pagination.page - 1) * pagination.page_size

        agents = await agent_service.list_public_agents(
            status=status,
            skip=offset,
            limit=pagination.page_size,
            only_official=only_official,
            only_hot=only_hot,
            category_id=category_id,
            session=session
        )
        return RestResponse(data=agents)
    except CustomAgentException as e:
        logger.error(f"Error listing public agents: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing public agents: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/agents/get", summary="Get Agent Details")
async def get_agent(
        agent_id: str = Query(None, description="agent id"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        agents = await agent_service.get_agent(agent_id, user, session=session)
        return RestResponse(data=agents)
    except CustomAgentException as e:
        logger.error(f"Error getting agent details: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting agent details: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.post("/agents/update", summary="Update Agent")
async def update_agent(
        agent: AgentDTO,
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Update an existing agent.
    """
    try:
        agent = await agent_service.update_agent(
            agent,
            user,
            session=session
        )
        return RestResponse(data=agent)
    except CustomAgentException as e:
        logger.error(f"Error updating agent: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating agent: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.delete("/agents/delete", summary="Delete Agent")
async def delete_agent(
        agent_id: str = Query(None, description="agent id"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Delete an agent by setting its is_deleted flag to True.

    - **agent_id**: ID of the agent to delete
    """
    try:
        await agent_service.delete_agent(agent_id, user, session)
        return RestResponse(data="ok")
    except CustomAgentException as e:
        logger.error(f"Error deleting agent: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting agent: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/agents/ai/create", summary="AI Create Agent")
async def ai_create_agent(
        description: Optional[str] = Query(None, description="description"),
        session: AsyncSession = Depends(get_db)):
    """
    Create a new agent.
    """
    try:
        resp = gen_agent(description)
        return StreamingResponse(content=resp, media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error in AI agent creation: {e}", exc_info=True)
        return RestResponse(
            code=ErrorCode.API_CALL_ERROR,
            msg=f"Failed to create AI agent: {str(e)}"
        )

@router.post("/agents/{agent_id}/dialogue")
async def dialogue(
        agent_id: str,
        request: DialogueRequest,
        user: Optional[dict] = Depends(get_optional_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Handle a dialogue between a user and an agent.

    - **agent_id**: ID of the agent to interact with
    - **message**: Message from the user
    """
    try:
        resp = agent_service.dialogue(agent_id, request, user, session)
        return StreamingResponse(content=resp, media_type="text/event-stream")
    except CustomAgentException as e:
        logger.error(f"Error in dialogue: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in dialogue: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/agents/{agent_id}/dialogue")
async def dialogue_get(
        request: Request,
        agent_id: str,
        query: str = Query(..., description="Query message from the user"),
        conversation_id: Optional[str] = Query(
            default=None,
            alias="conversationId",
            description="ID of the conversation"
        ),
        user: Optional[dict] = Depends(get_optional_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Handle a dialogue between a user and an agent using GET method.

    - **agent_id**: ID of the agent to interact with
    - **query**: Query message from the user
    - **conversation_id**: ID of the conversation (optional, auto-generated if not provided)
    """
    try:
        # Create a new DialogueRequest with default conversation_id if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        dialogue_request = DialogueRequest(
            query=query,
            conversationId=conversation_id
        )
        
        resp = agent_service.dialogue(agent_id, dialogue_request, user, session)
        return StreamingResponse(content=resp, media_type="text/event-stream")
    except CustomAgentException as e:
        logger.error(f"Error in dialogue: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in dialogue: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.post("/agents/{agent_id}/publish", summary="Publish Agent")
async def publish_agent(
        agent_id: str,
        is_public: bool = Query(True, description="Set agent as public"),
        create_fee: float = Query(0.0, description="Fee for creating the agent (tips for creator)"),
        price: float = Query(0.0, description="Fee for using the agent"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Publish or unpublish an agent with pricing settings

    Parameters:
    - **agent_id**: ID of the agent to publish
    - **is_public**: Whether to make the agent public
    - **create_fee**: Fee for creating the agent (tips for creator)
    - **price**: Fee for using the agent
    """
    try:
        await agent_service.publish_agent(agent_id, is_public, create_fee, price, user, session)
        return RestResponse(data="ok")
    except CustomAgentException as e:
        logger.error(f"Error publishing agent: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error publishing agent: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )
