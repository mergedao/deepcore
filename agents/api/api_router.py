import logging
import uuid

from fastapi import Query, APIRouter
from starlette.responses import StreamingResponse

from agents.agent.core.coins_agent import CoinAgent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/chat/completion")
async def completion(query: str = Query(default=""), conversationId: str = Query(default=str(uuid.uuid4()))):
    logger.info(f"query: {query}, conversationId: {conversationId}")
    agent = CoinAgent()
    resp = agent.arun(query, conversationId)
    return StreamingResponse(content=resp, media_type="text/event-stream")
