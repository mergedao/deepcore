from fastapi import Depends
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db
from agents.models.models import Tool
from agents.protocol.response import ToolModel
from agents.protocol.schemas import ToolType
from agents.utils import openapi


async def create_tool(app_id: int, name: str, type: ToolType, content: str, session: AsyncSession):
    new_tool = Tool(app_id=app_id, name=name, type=type.value, content=content)
    await check_oepnapi_validity(type, name, content)
    session.add(new_tool)
    await session.commit()
    return ToolModel(
        id=new_tool.id,
        app_id=new_tool.app_id,
        name=new_tool.name,
        type=new_tool.type,
        content=new_tool.content,
    )

async def update_tool(tool_id: int, name: str, type: ToolType = None, content: str = None,
                      session: AsyncSession = Depends(get_db)):
    values_to_update = {}
    if name is not None:
        values_to_update['name'] = name
    if type is not None:
        values_to_update['type'] = type.value
    if content is not None:
        await check_oepnapi_validity(type, name, content)
        values_to_update['content'] = content

    if values_to_update:
        stmt = update(Tool).where(Tool.id == tool_id) \
            .values(**values_to_update) \
            .execution_options(synchronize_session="fetch")
        await session.execute(stmt)
        await session.commit()
    return get_tool(tool_id, session)

async def delete_tool(tool_id: int, session: AsyncSession = Depends(get_db)):
    stmt = update(Tool).where(Tool.id == tool_id)\
        .values(is_deleted=True)\
        .execution_options(synchronize_session="fetch")
    await session.execute(stmt)
    await session.commit()

async def get_tool(tool_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if tool is None:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Invalid tool id")
    return ToolModel.from_orm(tool)

async def get_tools(app_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Tool).where(Tool.app_id == app_id))
    tools = result.scalars().all()
    return [ToolModel.from_orm(tool) for tool in tools]

async def check_oepnapi_validity(type: ToolType, name: str, content: str):
    if type != ToolType.OPENAPI:
        return

    validated, error = openapi.validate_openapi(content)
    if not validated:
        raise CustomAgentException(ErrorCode.OPENAPI_ERROR, f"{name} Invalid OpenApi definition error: {error}")
