import logging

import fastapi
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from agents.api import agent_router, api_router, file_router, tool_router, prompt_router, model_router, image_router
from agents.common.config import SETTINGS
from agents.common.log import Log
from agents.common.otel import Otel, OtelFastAPI
from agents.middleware.gobal import exception_handler
from agents.middleware.auth_middleware import JWTAuthMiddleware
from agents.api.auth_router import router as auth_router

logger = logging.getLogger(__name__)

app = FastAPI()


@app.exception_handler(Exception)
async def default_exception_handler(request: fastapi.Request, exc):
    return await exception_handler(request, exc)


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(api_router.router)
app.include_router(agent_router.router, prefix="/api", tags=["agent"])
app.include_router(model_router.router, prefix="/api", tags=["model"])
app.include_router(file_router.router, prefix="/api", tags=["file"])
app.include_router(tool_router.router, prefix="/api", tags=["tool"])
app.include_router(prompt_router.router, prefix="/api", tags=["prompt"])
app.include_router(image_router.router, prefix="/api", tags=["images"])

if __name__ == '__main__':
    Log.init()
    Otel.init()
    logger.info("Server started.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(JWTAuthMiddleware)
    
    OtelFastAPI.init(app)
    uvicorn.run(app, host=SETTINGS.HOST, port=SETTINGS.PORT)
