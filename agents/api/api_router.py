import logging
import uuid

from fastapi import Query, APIRouter
from starlette.responses import StreamingResponse

from agents.agent.coins_agent import CoinAgent
from .image_router import router as image_router
from agents.common.response import RestResponse

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(image_router)


async def health_check():
    """Health check endpoint that returns service status"""
    return RestResponse(data={"status": "ok"})


@router.get("/")
async def root():
    """Root endpoint that returns service status"""
    return await health_check()


@router.get("/api/health")
async def health():
    """Health check endpoint"""
    return await health_check()


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
        return RestResponse(code=1, msg=str(e))
