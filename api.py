import logging

import fastapi
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from agents.agent.tools.coin_tools import init_id_maps
from agents.api import agent_router, api_router, file_router, tool_router, prompt_router
from agents.common.config import SETTINGS
from agents.common.log import Log
from agents.common.otel import Otel, OtelFastAPI
from agents.middleware.gobal import exception_handler
from agents.middleware.http_security import APIKeyMiddleware

logger = logging.getLogger(__name__)

app = FastAPI()


@app.exception_handler(Exception)
async def default_exception_handler(request: fastapi.Request, exc):
    return await exception_handler(request, exc)


app.include_router(api_router.router)
app.include_router(agent_router.router, prefix="/api")
app.include_router(file_router.router, prefix="/api")
app.include_router(tool_router.router, prefix="/api")
app.include_router(prompt_router.router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")


def init_app():
    init_id_maps()


if __name__ == '__main__':
    Log.init()
    Otel.init()
    logger.info("Server started.")
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    init_app()
    OtelFastAPI.init(app)
    uvicorn.run(app, host=SETTINGS.HOST, port=SETTINGS.PORT)
