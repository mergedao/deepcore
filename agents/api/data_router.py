import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.error_messages import get_error_message
from agents.common.response import RestResponse
from agents.exceptions import CustomAgentException, ErrorCode
from agents.middleware.auth_middleware import get_optional_current_user
from agents.models.db import get_db
from agents.services.data_service import DataService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/data/xpro/hot", summary="Xpro Hot")
async def xpro_hot(
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Items per page"),
    user: Optional[dict] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get Xpro Hot data
    
    Parameters:
        - page: Page number, default is 1
        - page_size: Items per page, default is 10
    
    Returns:
        - List of Xpro Hot data
    """
    try:
        data_service = DataService(session)
        result = await data_service.get_xpro_hot(page, page_size)
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error getting xpro hot data: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting xpro hot data: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )

@router.get("/data/xpro/ca", summary="Xpro Ca")
async def xpro_ca(
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Items per page"),
    user: Optional[dict] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get Xpro Ca data
    
    Parameters:
        - page: Page number, default is 1
        - page_size: Items per page, default is 10
    
    Returns:
        - List of Xpro Ca data
    """
    try:
        data_service = DataService(session)
        result = await data_service.get_xpro_ca(page, page_size)
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error getting xpro ca data: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting xpro ca data: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        ) 