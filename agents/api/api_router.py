import logging
import uuid

from fastapi import Query, APIRouter, HTTPException, status
from starlette.responses import StreamingResponse, Response

from agents.agent.coins_agent import CoinAgent
from agents.common.response import RestResponse
from .image_router import router as image_router
from ..common.error_messages import get_error_message
from ..exceptions import ErrorCode
from ..models.db import detect_connection_leaks, get_pool_status

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(image_router)

@router.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return Response(status_code=204)  # 204 No Content


async def health_check():
    """
    Health check endpoint that returns service status
    Checks service status including database connection pool status
    """
    try:
        # Check database connection pool status
        leak_detected = await detect_connection_leaks(threshold_percentage=70)
        
        if leak_detected:
            # Connection leak detected, return 503 Service Unavailable
            logger.warning("Health check failed: Database connection pool usage is high")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection pool usage is high, possible connection leak detected"
            )
        
        return RestResponse(data={"status": "ok"})
    except HTTPException:
        # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Other exceptions return 500 error
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/")
async def root():
    """Root endpoint that returns service status"""
    return await health_check()


@router.get("/api/health")
async def health():
    """Health check endpoint"""
    return await health_check()


@router.get("/api/health/detailed")
async def health_detailed():
    """Detailed health check endpoint, includes database connection pool status details"""
    try:
        # Get connection pool status
        pool_status = await get_pool_status()
        
        # Detect potential connection leaks
        leak_detected = await detect_connection_leaks(threshold_percentage=70)
        
        response_data = {
            "status": "warning" if leak_detected else "ok",
            "database": {
                "pool_status": pool_status,
                "alert": "Connection pool usage is high, possible leak detected" if leak_detected else None
            }
        }
        
        # If connection leak detected, return 503 status code
        if leak_detected:
            logger.warning("Health check detailed: Database connection pool usage is high")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=response_data
            )
        
        return RestResponse(data=response_data)
    except HTTPException:
        # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Other exceptions return 500 error
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detailed health check failed: {str(e)}"
        )


@router.get("/api/chat/completion")
async def completion(query: str = Query(default=""), conversationId: str = Query(default=str(uuid.uuid4()))):
    """
    Chat completion endpoint that returns a streaming response
    """
    try:
        logger.info(f"query: {query}, conversationId: {conversationId}")
        agent = CoinAgent()
        resp = agent.stream(query, conversationId)
        return StreamingResponse(content=resp, media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error in chat completion: {e}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )
