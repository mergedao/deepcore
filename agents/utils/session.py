"""
Session and user information handling utilities
"""

import logging
from contextlib import asynccontextmanager
from starlette.requests import Request

logger = logging.getLogger(__name__)

async def get_async_session():
    """
    Get asynchronous database session
    
    Returns:
        Asynchronous database session
    """
    from agents.models.db import get_async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    
    engine = get_async_engine()
    async_session = AsyncSession(engine, expire_on_commit=False)
    
    return async_session

@asynccontextmanager
async def get_async_session_ctx():
    """
    Get database session supporting asynchronous context manager protocol
    
    Usage:
    async with get_async_session_ctx() as session:
        # Perform operations with session
    
    Returns:
        Database session supporting asynchronous context manager
    """
    session = await get_async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

async def get_user_from_request(request: Request) -> dict:
    """
    Extract user information from request
    
    Args:
        request: Starlette request object
        
    Returns:
        User information dictionary
    """
    try:
        # Get user information from request state
        user = request.state.user
        return user
    except AttributeError:
        # If no user information in request, use default values
        # In production, this should return None to indicate unauthenticated
        # But for development and testing purposes, we return a default user
        logger.warning("No user information found in request, using default user")
        return {
            "id": "default",
            "tenant_id": "default"
        } 