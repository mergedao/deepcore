from typing import List, Optional, AsyncIterator

from fastapi import Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agents.agent.core.chat_agent import ChatAgent
from agents.exceptions import CustomAgentException
from agents.models.db import get_db
from agents.models.models import App, Tool
from agents.protocol.response import AppModel
from agents.protocol.schemas import ToolInfo, AgentStatus, DialogueRequest
from agents.services import tool_service
from agents.services.tool_service import create_tool, update_tool


async def dialogue(agent_id: int, request: DialogueRequest, session: AsyncSession = Depends(get_db)) \
        -> AsyncIterator[str]:
    result = await session.execute(select(App).where(App.id == agent_id))
    agent = result.scalar_one_or_none()
    agent = ChatAgent(agent)
    async for response in agent.arun(request.query, request.conversation_id):
        yield response




async def get_agent(id: int, session: AsyncSession):
    result = await session.execute(select(App).where(App.id == id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise CustomAgentException(message=f'Agent not found')
    # Fetch tools for each agent
    model = AppModel.from_orm(agent)
    model.tools = await tool_service.get_tools(agent.id, session)
    return model


async def create_agent(
        name: str,
        description: str,
        mode: str = 'ReAct',
        icon: str = None,
        status: str = None,
        tool_prompt: str = None,
        max_loops: int = 5,
        tools: List[ToolInfo] = [],
        session: AsyncSession = Depends(get_db)):
    async with session.begin():
        new_agent = App(
            name=name,
            description=description,
            mode=mode,
            icon=icon,
            status=status,
            tool_prompt=tool_prompt,
            max_loops=max_loops,
        )
        session.add(new_agent)
        await session.flush()  # Ensure new_agent.id and new_agent.uuid are available

        # Create Tool records
        for tool in tools:
            await create_tool(
                app_id=new_agent.id,
                name=tool.name,
                type=tool.type,
                content=tool.content,
                session=session
            )

    return await get_agent(new_agent.id, session)

async def list_agents(status: Optional[AgentStatus], skip: int, limit: int, session: AsyncSession):
    query = select(App)
    if status:
        query = query.where(App.status == status)
    result = await session.execute(
        query.offset(skip).limit(limit)
    )
    agents = result.scalars().all()
    # Fetch tools for each agent
    results = []
    for agent in agents:
        model = AppModel.from_orm(agent)
        model.tools = await tool_service.get_tools(agent.id, session)
        results.append(model)

    return results

async def update_agent(
        agent_id: int,
        name: str = None,
        description: str = None,
        status: str = None,
        tool_prompt: str = None,
        max_loops: int = 5,
        tools: List[ToolInfo] = [],
        session: AsyncSession = Depends(get_db)):
    async with session.begin():
        # Check if the agent exists
        existing_agent = await session.execute(select(App).where(App.id == agent_id))
        existing_agent = existing_agent.scalar_one_or_none()
        if not existing_agent:
            raise CustomAgentException(f"Agent with ID {agent_id} does not exist.")

        # Update agent information in the App table
        stmt = update(App).where(App.id == agent_id)\
            .values(name=name, description=description, status=status, tool_prompt=tool_prompt, max_loops=max_loops)\
            .execution_options(synchronize_session="fetch")
        await session.execute(stmt)

        # Get existing tools for the agent
        existing_tools = await session.execute(select(Tool).where(Tool.app_id == agent_id))
        existing_tools = existing_tools.scalars().all()

        if tools:
            # Determine which tools to delete
            tool_ids_to_keep = {tool.id for tool in tools if tool.id is not None}
            tools_to_delete = [tool for tool in existing_tools if tool.id not in tool_ids_to_keep]

            # Delete tools that are not in the update list
            for tool in tools_to_delete:
                await session.delete(tool)

            # Update or create Tool records
            for tool in tools:
                if tool.id:
                    # If the tool exists, update it
                    existing_tool = next((t for t in existing_tools if t.id == tool.id), None)
                    if existing_tool:
                        await update_tool(
                            tool_id=existing_tool.id,
                            name=tool.name,
                            type=tool.type,
                            content=tool.content,
                            session=session
                        )
                else:
                    # If the tool does not exist, create it
                    await create_tool(
                        app_id=agent_id,
                        name=tool.name,
                        type=tool.type,
                        content=tool.content,
                        session=session
                    )
        else:
            # If tools list is empty, delete all existing tools
            for tool in existing_tools:
                await session.delete(tool)
    return await get_agent(agent_id, session)

async def delete_agent(agent_id: int, session: AsyncSession = Depends(get_db)):
    stmt = update(App).where(App.id == agent_id)\
        .values(is_deleted=True)\
        .execution_options(synchronize_session="fetch")
    await session.execute(stmt)
    await session.commit()