import logging

import fastapi
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from agents.agent.mcp import mcp_sse
from agents.api import agent_router, api_router, file_router, tool_router, prompt_router, model_router, image_router, category_router, open_router
from agents.api.data_router import router as data_router
from agents.common.config import SETTINGS
from agents.common.log import Log
from agents.common.otel import Otel, OtelFastAPI
from agents.middleware.gobal import exception_handler
from agents.middleware.auth_middleware import JWTAuthMiddleware
from agents.api.auth_router import router as auth_router
from agents.models.db import SessionLocal, dispose_engine
from agents.models.db_monitor import start_db_monitor, stop_db_monitor

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting database connection monitor...")
    # Use WARNING level by default to reduce log noise
    await start_db_monitor(log_level=logging.WARNING)
    
    yield  # This is where FastAPI serves requests
    
    # Shutdown logic
    logger.info("Stopping database connection monitor...")
    await stop_db_monitor()
    logger.info("Disposing database engine...")
    await dispose_engine()


def create_app() -> FastAPI:
    # Initialize logging and telemetry
    Log.init()
    Otel.init()
    logger.info("Server started.")

    app = FastAPI(lifespan=lifespan)

    # Add database session to app state
    app.state.db = SessionLocal

    # Add CORS middleware with more specific configuration
    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["*"],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    #     expose_headers=["*"],
    #     max_age=600,  # Cache preflight requests for 10 minutes
    # )

    # Add JWT middleware
    app.add_middleware(JWTAuthMiddleware)

    @app.exception_handler(Exception)
    async def default_exception_handler(request: fastapi.Request, exc):
        return await exception_handler(request, exc)

    # Include routers
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(api_router.router)
    app.include_router(agent_router.router, prefix="/api", tags=["agent"])
    app.include_router(model_router.router, prefix="/api", tags=["model"])
    app.include_router(file_router.router, prefix="/api", tags=["file"])
    app.include_router(tool_router.router, prefix="/api", tags=["tool"])
    app.include_router(prompt_router.router, prefix="/api", tags=["prompt"])
    app.include_router(image_router.router, prefix="/api", tags=["images"])
    app.include_router(category_router.router, prefix="/api", tags=["category"])
    app.include_router(open_router.router, prefix="/api/open", tags=["open"])
    app.include_router(data_router, prefix="/api/p", tags=["data"])

    # add mcp
    app.mount("/", mcp_sse.get_all_routers())

    # Initialize OpenTelemetry
    OtelFastAPI.init(app)

    return app


app = create_app()

if __name__ == '__main__':
    uvicorn.run(app, host=SETTINGS.HOST, port=SETTINGS.PORT)
