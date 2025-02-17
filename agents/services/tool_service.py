from fastapi import Depends
from sqlalchemy import update, select, or_, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db
from agents.models.models import Tool, App, AgentTool
from agents.protocol.response import ToolModel
from agents.protocol.schemas import ToolType, AuthConfig
from agents.utils import openapi


def tool_to_dto(tool: Tool) -> ToolModel:
    """Convert Tool ORM object to DTO"""
    return ToolModel(
        id=tool.id,
        name=tool.name,
        type=tool.type,
        content=tool.content,
        auth_config=tool.auth_config,
        is_public=tool.is_public,
        is_official=tool.is_official,
        tenant_id=tool.tenant_id,
        create_time=tool.create_time,
        update_time=tool.update_time
    )


async def create_tool(
        name: str, 
        type: ToolType, 
        content: str,
        user: dict,
        session: AsyncSession,
        auth_config: Optional[AuthConfig] = None
):
    """
    Create tool with user context
    """
    new_tool = Tool(
        name=name, 
        type=type.value, 
        content=content,
        is_public=False,
        is_official=False,
        auth_config=auth_config.model_dump() if auth_config else None,
        tenant_id=user.get('tenant_id')
    )
    await check_oepnapi_validity(type, name, content)
    session.add(new_tool)
    await session.commit()
    return tool_to_dto(new_tool)


async def update_tool(
        tool_id: int,
        user: dict,
        session: AsyncSession,
        name: Optional[str] = None,
        type: Optional[ToolType] = None,
        content: Optional[str] = None,
        auth_config: Optional[AuthConfig] = None
):
    # Verify if the tool belongs to current user
    tool_result = await session.execute(
        select(Tool).where(
            Tool.id == tool_id,
            Tool.tenant_id == user.get('tenant_id')
        )
    )
    tool = tool_result.scalar_one_or_none()
    if not tool:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Tool not found or no permission")

    values_to_update = {}
    if name is not None:
        values_to_update['name'] = name
    if type is not None:
        values_to_update['type'] = type.value
    if content is not None:
        await check_oepnapi_validity(type, name, content)
        values_to_update['content'] = content
    if auth_config is not None:
        values_to_update['auth_config'] = auth_config.model_dump()

    if values_to_update:
        stmt = update(Tool).where(
            Tool.id == tool_id,
            Tool.tenant_id == user.get('tenant_id')
        ).values(**values_to_update).execution_options(synchronize_session="fetch")
        await session.execute(stmt)
        await session.commit()
    return get_tool(tool_id, user, session)


async def delete_tool(
        tool_id: int, 
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    stmt = update(Tool).where(
        Tool.id == tool_id,
        Tool.tenant_id == user.get('tenant_id')
    ).values(is_deleted=True).execution_options(synchronize_session="fetch")
    await session.execute(stmt)
    await session.commit()


async def get_tool(
        tool_id: int, 
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    result = await session.execute(
        select(Tool).where(
            Tool.id == tool_id,
            Tool.tenant_id == user.get('tenant_id')
        )
    )
    tool = result.scalar_one_or_none()
    if tool is None:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Tool not found or no permission")
    return ToolModel.model_validate(tool)


async def get_tools(
        session: AsyncSession,
        user: dict,
        include_public: bool = True,
        only_official: bool = False
):
    """
    List tools with filters for public and official tools
    """
    conditions = []
    
    if only_official:
        conditions.append(Tool.is_official == True)
    else:
        if user and user.get('tenant_id'):
            conditions.append(
                or_(
                    Tool.tenant_id == user.get('tenant_id'),
                    and_(Tool.is_public == True) if include_public else False
                )
            )
        else:
            conditions.append(Tool.is_public == True)
            
    # Remove app_id filter since we use AgentTool for associations
    result = await session.execute(
        select(Tool).where(and_(*conditions))
    )
    tools = result.scalars().all()
    return [ToolModel.model_validate(tool) for tool in tools]


async def check_oepnapi_validity(type: ToolType, name: str, content: str):
    if type != ToolType.OPENAPI:
        return

    validated, error = openapi.validate_openapi(content)
    if not validated:
        raise CustomAgentException(ErrorCode.OPENAPI_ERROR, f"{name} Invalid OpenApi definition error: {error}")


async def publish_tool(
        tool_id: int,
        is_public: bool,
        user: dict,
        session: AsyncSession):
    """
    Publish or unpublish a tool
    """
    # First check if the tool exists and belongs to the user's tenant
    result = await session.execute(
        select(Tool).where(
            Tool.id == tool_id,
            Tool.tenant_id == user.get('tenant_id')
        )
    )
    tool = result.scalar_one_or_none()
    if not tool:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Tool not found or no permission")

    # If tool exists and belongs to user's tenant, proceed with publish/unpublish
    stmt = update(Tool).where(
        Tool.id == tool_id,
        Tool.tenant_id == user.get('tenant_id')
    ).values(
        is_public=is_public
    )
    await session.execute(stmt)
    await session.commit()


async def assign_tool_to_agent(
        tool_id: int,
        agent_id: str,
        user: dict,
        session: AsyncSession
):
    """
    Assign a tool to an agent
    """
    # Check if tool exists and is accessible (owned or public)
    tool = await session.execute(
        select(Tool).where(
            or_(
                Tool.tenant_id == user.get('tenant_id'),
                Tool.is_public == True
            ),
            Tool.id == tool_id
        )
    )
    tool = tool.scalar_one_or_none()
    if not tool:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Tool not found or no permission")

    # Check if agent belongs to user
    agent = await session.execute(
        select(App).where(
            App.id == agent_id,
            App.tenant_id == user.get('tenant_id')
        )
    )
    agent = agent.scalar_one_or_none()
    if not agent:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Agent not found or no permission")

    # Create association
    agent_tool = AgentTool(
        agent_id=agent_id,
        tool_id=tool_id,
        tenant_id=user.get('tenant_id')
    )
    session.add(agent_tool)
    await session.commit()


async def remove_tool_from_agent(
        tool_id: int,
        agent_id: str,
        user: dict,
        session: AsyncSession
):
    """
    Remove a tool from an agent
    """
    await session.execute(
        delete(AgentTool).where(
            AgentTool.agent_id == agent_id,
            AgentTool.tool_id == tool_id,
            AgentTool.tenant_id == user.get('tenant_id')
        )
    )
    await session.commit()


async def get_agent_tools(
        agent_id: str,
        user: dict,
        session: AsyncSession
):
    """
    Get all tools associated with an agent
    """
    result = await session.execute(
        select(Tool).join(AgentTool).where(
            AgentTool.agent_id == agent_id,
            AgentTool.tenant_id == user.get('tenant_id')
        )
    )
    tools = result.scalars().all()
    return [ToolModel.model_validate(tool) for tool in tools]


async def assign_tools_to_agent(
        tool_ids: List[int],
        agent_id: str,
        user: dict,
        session: AsyncSession
):
    """
    Assign multiple tools to an agent
    """
    # Check if agent belongs to user
    agent = await session.execute(
        select(App).where(
            App.id == agent_id,
            App.tenant_id == user.get('tenant_id')
        )
    )
    agent = agent.scalar_one_or_none()
    if not agent:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Agent not found or no permission")

    # Check if all tools exist and are accessible (owned or public)
    tools = await session.execute(
        select(Tool).where(
            or_(
                Tool.tenant_id == user.get('tenant_id'),
                Tool.is_public == True
            ),
            Tool.id.in_(tool_ids)
        )
    )
    found_tools = tools.scalars().all()
    if len(found_tools) != len(tool_ids):
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Some tools not found or no permission")

    # Create associations
    for tool_id in tool_ids:
        agent_tool = AgentTool(
            agent_id=agent_id,
            tool_id=tool_id,
            tenant_id=user.get('tenant_id')
        )
        session.add(agent_tool)
    
    await session.commit()


async def remove_tools_from_agent(
        tool_ids: List[int],
        agent_id: str,
        user: dict,
        session: AsyncSession
):
    """
    Remove multiple tools from an agent
    """
    await session.execute(
        delete(AgentTool).where(
            AgentTool.agent_id == agent_id,
            AgentTool.tool_id.in_(tool_ids),
            AgentTool.tenant_id == user.get('tenant_id')
        )
    )
    await session.commit()


# Add a new function to get tools by agent
async def get_tools_by_agent(
        agent_id: str,
        session: AsyncSession,
        user: dict,
):
    """
    Get all tools associated with a specific agent
    """
    result = await session.execute(
        select(Tool).join(AgentTool).where(
            AgentTool.agent_id == agent_id,
            AgentTool.tenant_id == user.get('tenant_id')
        )
    )
    tools = result.scalars().all()
    return [ToolModel.model_validate(tool) for tool in tools]
