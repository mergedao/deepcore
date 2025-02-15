from typing import Optional, AsyncIterator

from fastapi import Depends
from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agents.agent.chat_agent import ChatAgent
from agents.exceptions import CustomAgentException
from agents.models.db import get_db
from agents.models.models import App
from agents.protocol.schemas import AgentStatus, DialogueRequest, AgentDTO


async def dialogue(agent_id: int, request: DialogueRequest, session: AsyncSession = Depends(get_db)) \
        -> AsyncIterator[str]:
    result = await session.execute(select(App).where(App.id == agent_id))
    agent = result.scalar_one_or_none()
    agent = ChatAgent(agent)
    async for response in agent.stream(request.query, request.conversation_id):
        yield response


async def get_agent(id: str, session: AsyncSession):
    result = await session.execute(select(App).where(App.id == id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise CustomAgentException(message=f'Agent not found')
    # Fetch tools for each agent
    model = AgentDTO.model_validate_json(agent.model_json)
    # model.tools = await tool_service.get_tools(agent.id, session)
    return model


async def create_agent(
        agent: AgentDTO,
        session: AsyncSession = Depends(get_db)):
    async with session.begin():
        new_agent = App(
            id=agent.id,
            name=agent.name,
            mode=agent.mode,
            status=agent.status,
            model_json=agent.model_dump_json(),
        )
        session.add(new_agent)
        await session.flush()  # Ensure new_agent.id and new_agent.uuid are available

        # Create Tool records
        # for tool in tools:
        #     await create_tool(
        #         app_id=new_agent.id,
        #         name=tool.name,
        #         type=tool.type,
        #         content=tool.content,
        #         session=session
        #     )

    return agent


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
        model = AgentDTO.model_validate_json(agent.model_json)
        # model.tools = await tool_service.get_tools(agent.id, session)
        results.append(model)

    return results


async def update_agent(
        agent: AgentDTO,
        session: AsyncSession = Depends(get_db)):
    async with session.begin():
        # Check if the agent exists

        agent_model = await get_agent(agent.id, session)

        for key, value in agent.model_dump().items():
            if value is not None:
                setattr(agent_model, key, value)

        # Update agent information in the App table
        stmt = update(App).where(App.id == agent_model.id) \
            .values(name=agent_model.name,
                    mode=agent_model.mode,
                    status=agent_model.status,
                    model_json=agent_model.model_dump_json()) \
            .execution_options(synchronize_session="fetch")
        await session.execute(stmt)

        # Get existing tools for the agent
        # existing_tools = await session.execute(select(Tool).where(Tool.app_id == agent_id))
        # existing_tools = existing_tools.scalars().all()

        # if tools:
        #     # Determine which tools to delete
        #     tool_ids_to_keep = {tool.id for tool in tools if tool.id is not None}
        #     tools_to_delete = [tool for tool in existing_tools if tool.id not in tool_ids_to_keep]
        #
        #     # Delete tools that are not in the update list
        #     for tool in tools_to_delete:
        #         await session.delete(tool)
        #
        #     # Update or create Tool records
        #     for tool in tools:
        #         if tool.id:
        #             # If the tool exists, update it
        #             existing_tool = next((t for t in existing_tools if t.id == tool.id), None)
        #             if existing_tool:
        #                 await update_tool(
        #                     tool_id=existing_tool.id,
        #                     name=tool.name,
        #                     type=tool.type,
        #                     content=tool.content,
        #                     session=session
        #                 )
        #         else:
        #             # If the tool does not exist, create it
        #             await create_tool(
        #                 app_id=agent_id,
        #                 name=tool.name,
        #                 type=tool.type,
        #                 content=tool.content,
        #                 session=session
        #             )
        # else:
        #     # If tools list is empty, delete all existing tools
        #     for tool in existing_tools:
        #         await session.delete(tool)
    return agent_model


async def delete_agent(agent_id: str, session: AsyncSession = Depends(get_db)):
    await session.execute(delete(App).where(App.id == agent_id))
    await session.commit()
