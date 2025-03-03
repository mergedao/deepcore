import json
import logging
from typing import Optional, AsyncIterator, List

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy import update, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from agents.agent.chat_agent import ChatAgent
from agents.common.config import SETTINGS
from agents.common.encryption_utils import encryption_utils
from agents.common.redis_utils import redis_utils
from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db
from agents.models.entity import AgentInfo, ModelInfo, ChatContext
from agents.models.models import App, Tool, AgentTool
from agents.protocol.schemas import AgentStatus, DialogueRequest, AgentDTO, ToolInfo, CategoryDTO
from agents.services.model_service import get_model_with_key, get_model

logger = logging.getLogger(__name__)


async def dialogue(
        agent_id: str,
        request: DialogueRequest,
        user: Optional[dict],
        session: AsyncSession = Depends(get_db)
) -> AsyncIterator[str]:
    # Add tenant filter
    agent = await get_agent(agent_id, user, session)
    agent_info = AgentInfo.from_dto(agent)
    
    # Set up model info if specified
    if agent.model_id:
        model_dto, api_key = await get_model_with_key(agent.model_id, user, session)
        model_info = ModelInfo(**model_dto.model_dump())
        model_info.api_key = api_key
        agent_info.set_model(model_info)
    
    if not agent:
        raise CustomAgentException(
            ErrorCode.RESOURCE_NOT_FOUND,
            "Agent not found or no permission"
        )

    # Get the initialization flag
    chat_context = ChatContext(
        init_flag=request.initFlag if hasattr(request, 'initFlag') else False
    )
    # Create appropriate agent based on mode
    agent = ChatAgent(agent_info, chat_context)
    
    # Stream the response
    async for response in agent.stream(request.query, request.conversation_id):
        yield response


async def get_agent(id: str, user: Optional[dict], session: AsyncSession):
    """
    Get agent with its associated tools
    """
    # Build base query conditions
    conditions = [App.id == id]
    
    # If user is logged in, add tenant filter or public agent condition
    if user and user.get('tenant_id'):
        conditions.append(or_(
            App.tenant_id == user.get('tenant_id'),
            App.is_public == True
        ))
    else:
        # Non-logged-in users can only access public agents
        conditions.append(App.is_public == True)

    # Execute query
    result = await session.execute(
        select(App).where(and_(*conditions))
    )
    agent = result.scalar_one_or_none()
    
    if agent is None:
        raise CustomAgentException(
            ErrorCode.RESOURCE_NOT_FOUND,
            "Agent not found or no permission"
        )

    # Get associated tools
    tool_conditions = [AgentTool.agent_id == id, Tool.is_deleted == False]
    if user and user.get('tenant_id'):
        tool_conditions.append(or_(
            AgentTool.tenant_id == user.get('tenant_id'),
            Tool.is_public == True
        ))
    else:
        tool_conditions.append(Tool.is_public == True)

    tools_result = await session.execute(
        select(Tool).join(AgentTool).where(and_(*tool_conditions))
    )
    tools = tools_result.scalars().all()

    # Get model info if model_id exists
    model = None
    if agent.model_id:
        try:
            model = await get_model(agent.model_id, user, session)
        except Exception as e:
            logger.warning(f"Failed to get model info for agent {agent.id}: {e}")

    # Convert to DTO
    try:
        # Process telegram bot token if exists
        masked_token = None
        if agent.telegram_bot_token:
            masked_token = mask_token(decrypt_token(agent.telegram_bot_token))
            
        # Parse model_json if exists
        shouldInitializeDialog = False
        if agent.model_json:
            try:
                model_json_data = json.loads(agent.model_json)
                shouldInitializeDialog = model_json_data.get("shouldInitializeDialog", False)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse model_json for agent {agent.id}")
            
        # Convert App model to AgentDTO
        agent_dto = AgentDTO(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            mode=agent.mode,
            icon=agent.icon,
            status=agent.status,
            role_settings=agent.role_settings,
            welcome_message=agent.welcome_message,
            twitter_link=agent.twitter_link,
            telegram_bot_id=agent.telegram_bot_id,
            telegram_bot_name=agent.telegram_bot_name,
            telegram_bot_token=masked_token,
            tool_prompt=agent.tool_prompt,
            max_loops=agent.max_loops,
            suggested_questions=agent.suggested_questions,
            model_id=agent.model_id,
            model=model,  # Add model info to DTO
            is_public=agent.is_public,
            is_official=agent.is_official,
            shouldInitializeDialog=shouldInitializeDialog
        )

        # Add tools to the DTO
        agent_dto.tools = [ToolInfo(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            type=tool.type,
            origin=tool.origin,
            path=tool.path,
            method=tool.method,
            parameters=tool.parameters,
            auth_config=tool.auth_config,
            is_public=tool.is_public,
            is_official=tool.is_official,
            tenant_id=tool.tenant_id,
            is_stream=tool.is_stream,
            output_format=tool.output_format
        ) for tool in tools]

        return agent_dto
    except Exception as e:
        logger.error(f"Error converting agent to DTO: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            "Error processing agent data"
        )


async def verify_tool_permissions(
        tool_ids: List[int],
        user: dict,
        session: AsyncSession
) -> List[Tool]:
    """
    Verify if user has permission to use the specified tools
    Raises CustomAgentException if any tool is not accessible
    """
    if not tool_ids:
        return []

    tools = await session.execute(
        select(Tool).where(
            and_(
                Tool.id.in_(tool_ids),
                or_(
                    Tool.tenant_id == user.get('tenant_id'),
                    Tool.is_public == True
                )
            )
        )
    )
    found_tools = tools.scalars().all()

    if len(found_tools) != len(tool_ids):
        inaccessible_tools = set(tool_ids) - {tool.id for tool in found_tools}
        raise CustomAgentException(
            ErrorCode.PERMISSION_DENIED,
            f"No permission to access tools: {inaccessible_tools}"
        )

    return found_tools


async def create_agent(
        agent: AgentDTO,
        user: dict,
        session: AsyncSession = Depends(get_db)):
    """
    Create a new agent with user context and tools
    """
    if not user.get('tenant_id'):
        raise CustomAgentException(
            ErrorCode.UNAUTHORIZED,
            "User must belong to a tenant to create agents"
        )

    try:
        async with session.begin():
            # Verify tool permissions if tools are specified
            tool_ids = []
            if agent.tools:
                tool_ids = agent.tools
                await verify_tool_permissions(tool_ids, user, session)

            # Extract specific fields for model_json
            model_json_data = {}
            if agent.shouldInitializeDialog is not None:
                model_json_data["shouldInitializeDialog"] = agent.shouldInitializeDialog

            new_agent = App(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                mode=agent.mode,
                icon=agent.icon,
                status=agent.status,
                role_settings=agent.role_settings,
                welcome_message=agent.welcome_message,
                twitter_link=agent.twitter_link,
                telegram_bot_id=agent.telegram_bot_id,
                tool_prompt=agent.tool_prompt,
                max_loops=agent.max_loops,
                suggested_questions=agent.suggested_questions,
                model_id=agent.model_id,
                category_id=agent.category_id,
                model_json=json.dumps(model_json_data) if model_json_data else None,
                tenant_id=user.get('tenant_id')
            )
            session.add(new_agent)
            await session.flush()

            # Create tool associations
            for tool_id in tool_ids:
                agent_tool = AgentTool(
                    agent_id=new_agent.id,
                    tool_id=tool_id,
                    tenant_id=user.get('tenant_id')
                )
                session.add(agent_tool)

            return agent
    except Exception as e:
        logger.error(f"Error creating agent: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to create agent: {str(e)}"
        )


async def list_personal_agents(
        status: Optional[AgentStatus],
        skip: int,
        limit: int,
        session: AsyncSession,
        user: dict,
        include_public: bool = False,
        category_id: Optional[int] = None
):
    """
    List user's personal agents

    Args:
        status: Optional filter for agent status
        skip: Number of records to skip ((page - 1) * page_size)
        limit: Number of records per page (page_size)
        session: Database session
        user: Current user info
        include_public: Whether to include public agents along with personal agents
        category_id: Optional filter for category ID

    Returns:
        dict: {
            "items": list of agents,
            "total": total number of records,
            "page": current page number,
            "page_size": number of items per page,
            "total_pages": total number of pages
        }
    """
    if not user or not user.get('tenant_id'):
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0
        }

    conditions = [App.tenant_id == user.get('tenant_id')]

    if include_public:
        conditions.append(App.tenant_id == user.get('tenant_id') or App.is_public == True)

    if status:
        conditions.append(App.status == status)
        
    if category_id:
        conditions.append(App.category_id == category_id)

    return await _get_paginated_agents(conditions, skip, limit, user, session)


async def list_public_agents(
        status: Optional[AgentStatus],
        skip: int,
        limit: int,
        session: AsyncSession,
        only_official: bool = False,
        only_hot: bool = False,
        category_id: Optional[int] = None,
        user: Optional[dict] = None
):
    """
    List public or official agents

    Args:
        status: Optional filter for agent status
        skip: Number of records to skip ((page - 1) * page_size)
        limit: Number of records per page (page_size)
        session: Database session
        only_official: Whether to only show official agents
        only_hot: Whether to only show hot agents
        category_id: Optional filter for category ID
        user: Optional user information for token decryption

    Returns:
        dict: {
            "items": list of agents,
            "total": total number of records,
            "page": current page number,
            "page_size": number of items per page,
            "total_pages": total number of pages
        }
    """
    conditions = []

    if only_official:
        conditions.append(App.is_official == True)
    elif only_hot:
        conditions.append(App.is_hot == True)
    else:
        conditions.append(App.is_public == True)

    if status:
        conditions.append(App.status == status)
        
    if category_id:
        conditions.append(App.category_id == category_id)

    return await _get_paginated_agents(conditions, skip, limit, user, session)


async def _get_paginated_agents(conditions: list, skip: int, limit: int, user: Optional[dict], session: AsyncSession):
    """
    Helper function to get paginated agents with given conditions
    """
    # Calculate total count for pagination info
    count_query = select(func.count()).select_from(App).where(and_(*conditions))
    total_count = await session.execute(count_query)
    total_count = total_count.scalar()

    # Get paginated results with ordering
    query = (
        select(App)
        .options(selectinload(App.category))
        .where(and_(*conditions))
        .order_by(App.create_time.desc())
    )

    result = await session.execute(
        query.offset(skip).limit(limit)
    )
    agents = result.scalars().all()
    results = []

    for agent in agents:
        # Get associated tools for each agent
        tools_result = await session.execute(
            select(Tool).join(AgentTool).where(
                AgentTool.agent_id == agent.id,
                Tool.is_deleted == False,
                # Only filter by tenant_id for personal tools
                *([AgentTool.tenant_id == user.get('tenant_id')] if user else [])
            )
        )
        tools = tools_result.scalars().all()

        # Get model info if model_id exists
        model = None
        if agent.model_id:
            try:
                model = await get_model(agent.model_id, user, session)
            except Exception as e:
                logger.warning(f"Failed to get model info for agent {agent.id}: {e}")
                
        # Parse model_json if exists
        shouldInitializeDialog = False
        if agent.model_json:
            try:
                model_json_data = json.loads(agent.model_json)
                shouldInitializeDialog = model_json_data.get("shouldInitializeDialog", False)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse model_json for agent {agent.id}")
                
        # Process telegram bot token if exists
        masked_token = None
        if agent.telegram_bot_token:
            masked_token = mask_token(decrypt_token(agent.telegram_bot_token))

        # Convert to DTO
        agent_dto = AgentDTO(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            mode=agent.mode,
            icon=agent.icon,
            status=agent.status,
            role_settings=agent.role_settings,
            welcome_message=agent.welcome_message,
            twitter_link=agent.twitter_link,
            telegram_bot_id=agent.telegram_bot_id,
            telegram_bot_name=agent.telegram_bot_name,
            telegram_bot_token=masked_token,
            tool_prompt=agent.tool_prompt,
            max_loops=agent.max_loops,
            suggested_questions=agent.suggested_questions,
            model_id=agent.model_id,
            model=model,  # Add model info to DTO
            category_id=agent.category_id,
            is_public=agent.is_public,
            is_official=agent.is_official,
            is_hot=agent.is_hot,
            create_fee=float(agent.create_fee) if agent.create_fee else None,
            price=float(agent.price) if agent.price else None,
            shouldInitializeDialog=shouldInitializeDialog,
            tools=[ToolInfo(
                id=tool.id,
                name=tool.name,
                type=tool.type,
                origin=tool.origin,
                path=tool.path,
                method=tool.method,
                parameters=tool.parameters
            ) for tool in tools]
        )

        if agent.category:
            agent_dto.category = CategoryDTO(
                id=agent.category.id,
                name=agent.category.name,
                type=agent.category.type,
                description=agent.category.description,
                tenant_id=agent.category.tenant_id,
                sort_order=agent.category.sort_order,
                create_time=agent.category.create_time.isoformat() if agent.category.create_time else None,
                update_time=agent.category.update_time.isoformat() if agent.category.update_time else None
            )

        results.append(agent_dto)

    # Calculate current page from skip and limit
    current_page = (skip // limit) + 1

    return {
        "items": results,
        "total": total_count,
        "page": current_page,
        "page_size": limit,
        "total_pages": (total_count + limit - 1) // limit
    }


async def update_agent(
        agent: AgentDTO,
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    """
    Update an existing agent
    """
    if not agent.id:
        raise CustomAgentException(
            ErrorCode.INVALID_REQUEST,
            "Agent ID is required for update"
        )

    try:
        async with session.begin():
            # Check if agent exists and belongs to the user's tenant
            result = await session.execute(
                select(App).where(
                    App.id == agent.id,
                    App.tenant_id == user.get('tenant_id')
                )
            )
            existing_agent = result.scalar_one_or_none()
            
            if not existing_agent:
                raise CustomAgentException(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "Agent not found or no permission to update"
                )

            # Verify tool permissions if tools are specified
            if agent.tools:
                await verify_tool_permissions(agent.tools, user, session)

            # Extract specific fields for model_json
            model_json_data = {}
            if agent.shouldInitializeDialog is not None:
                model_json_data["shouldInitializeDialog"] = agent.shouldInitializeDialog
            
            # If there was existing model_json data, preserve it and update only what's needed
            if existing_agent.model_json:
                try:
                    existing_model_json = json.loads(existing_agent.model_json)
                    # Update with new values, keeping any existing values not being updated
                    existing_model_json.update(model_json_data)
                    model_json_data = existing_model_json
                except (json.JSONDecodeError, TypeError):
                    # If existing model_json is invalid, just use the new data
                    pass

            # Update agent fields
            existing_agent.name = agent.name
            existing_agent.description = agent.description
            existing_agent.mode = agent.mode
            existing_agent.icon = agent.icon
            existing_agent.status = agent.status
            existing_agent.role_settings = agent.role_settings
            existing_agent.welcome_message = agent.welcome_message
            existing_agent.twitter_link = agent.twitter_link
            existing_agent.tool_prompt = agent.tool_prompt
            existing_agent.max_loops = agent.max_loops
            existing_agent.suggested_questions = agent.suggested_questions
            existing_agent.model_id = agent.model_id
            existing_agent.category_id = agent.category_id
            existing_agent.model_json = json.dumps(model_json_data) if model_json_data else None

            # Update tool associations
            if agent.tools:
                # Remove existing tool associations
                await session.execute(
                    delete(AgentTool).where(
                        AgentTool.agent_id == agent.id,
                        AgentTool.tenant_id == user.get('tenant_id')
                    )
                )
                
                # Create new tool associations
                for tool_id in agent.tools:
                    agent_tool = AgentTool(
                        agent_id=agent.id,
                        tool_id=tool_id,
                        tenant_id=user.get('tenant_id')
                    )
                    session.add(agent_tool)

            return agent
    except CustomAgentException:
        logger.error(f"Error updating agent: ", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error updating agent: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to update agent: {str(e)}"
        )


async def delete_agent(
        agent_id: str,
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    try:
        async with session.begin():
            # Verify agent exists and belongs to user
            result = await session.execute(
                select(App).where(
                    App.id == agent_id,
                    App.tenant_id == user.get('tenant_id')
                )
            )
            if not result.scalar_one_or_none():
                raise CustomAgentException(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "Agent not found or no permission to delete"
                )

            # Delete agent
            await session.execute(
                delete(App).where(
                    App.id == agent_id,
                    App.tenant_id == user.get('tenant_id')
                )
            )
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to delete agent: {str(e)}"
        )


async def publish_agent(
        agent_id: str,
        is_public: bool,
        create_fee: float,
        price: float,
        user: dict,
        session: AsyncSession):
    """
    Publish or unpublish an agent

    Args:
        agent_id: ID of the agent
        is_public: Whether to make the agent public
        create_fee: Fee for creating the agent (tips for creator)
        price: Fee for using the agent
        user: Current user info
        session: Database session
    """
    try:
        async with session.begin():
            # First check if the agent exists and belongs to the user's tenant
            result = await session.execute(
                select(App).where(
                    App.id == agent_id,
                    App.tenant_id == user.get('tenant_id')
                )
            )
            agent = result.scalar_one_or_none()
            if not agent:
                raise CustomAgentException(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "Agent not found or no permission"
                )

            # Update publish status and fees
            stmt = update(App).where(
                App.id == agent_id,
                App.tenant_id == user.get('tenant_id')
            ).values(
                is_public=is_public,
                create_fee=create_fee,
                price=price
            )
            await session.execute(stmt)
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error publishing agent: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to publish agent: {str(e)}"
        )

# Encryption function
def encrypt_token(token: str) -> str:
    """Encrypt Telegram bot token"""
    return encryption_utils.encrypt(token)

# Decryption function
def decrypt_token(encrypted_token: str) -> str:
    """Decrypt Telegram bot token"""
    return encryption_utils.decrypt(encrypted_token)

# Masking function, used to hide the middle part of the token
def mask_token(token: str) -> str:
    """Mask the middle part of the token with asterisks"""
    return encryption_utils.mask_token(token)

async def register_telegram_bot(
        agent_id: str,
        bot_name: str,
        token: str,
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    """
    Register an agent as a Telegram bot
    
    Args:
        agent_id: Agent ID
        bot_name: Telegram bot name
        token: Telegram bot token
        user: Current user information
        session: Database session
    """
    try:
        # Verify if agent exists and belongs to current user
        result = await session.execute(
            select(App).where(
                App.id == agent_id,
                App.tenant_id == user.get('tenant_id')
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise CustomAgentException(
                ErrorCode.RESOURCE_NOT_FOUND,
                "Agent not found or no permission"
            )
        
        # Encrypt token
        encrypted_token = encrypt_token(token)
        
        # Update agent table with telegram bot info
        stmt = update(App).where(
            App.id == agent_id,
            App.tenant_id == user.get('tenant_id')
        ).values(
            telegram_bot_name=bot_name,
            telegram_bot_token=encrypted_token
        )
        await session.execute(stmt)
        await session.commit()
        
        # Update bot information in Redis
        await update_telegram_bots_redis(user, session)
        
        # Return masked token
        masked_token = mask_token(token)
        
        return {
            "agent_id": agent_id,
            "bot_name": bot_name,
            "token": masked_token
        }
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error registering Telegram bot: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to register Telegram bot: {str(e)}"
        )

async def update_telegram_bots_redis(user: dict,session: AsyncSession):
    """
    Update Telegram bot information in Redis
    """
    try:
        import json
        from agents.services.open_service import get_or_create_credentials
        
        # Query all agents with Telegram bot token
        result = await session.execute(
            select(App).where(
                App.telegram_bot_token.is_not(None)
            )
        )
        agents = result.scalars().all()
        
        bots_info = []
        for agent in agents:
            # Decrypt token
            token = decrypt_token(agent.telegram_bot_token)
            if not token:
                continue
                
            # Get open platform credentials for the agent's tenant
            try:
                credentials = await get_or_create_credentials(user, session)
                access_key = credentials.get("access_key")
                secret_key = credentials.get("secret_key")
                
                # Build agent URL
                agent_url = f"{SETTINGS.API_BASE_URL}/api/agents/{agent.id}/dialogue"
                
                bot_info = {
                    "token": token,
                    "access_key": access_key,
                    "secret_key": secret_key,
                    "agent_url": agent_url,
                    "agent_name": agent.name,
                    "agent_description": agent.description or ""
                }
                bots_info.append(bot_info)
            except Exception as e:
                logger.error(f"Error getting credentials for agent {agent.id}: {e}")
                continue
        
        # Store bot information in Redis
        if bots_info:
            redis_key = f"{SETTINGS.TELEGRAM_REDIS_KEY}_{SETTINGS.REDIS_PREFIX}"
            redis_utils.set_value(redis_key, json.dumps(bots_info))
            logger.info(f"Updated {len(bots_info)} Telegram bots in Redis")
        
    except Exception as e:
        logger.error(f"Error updating Telegram bots in Redis: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to update Telegram bots in Redis: {str(e)}"
        )
