import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.app.api.auth import auth_router
from src.app.api.ping import ping_router
from src.app.core.config import settings
from src.app.db.postgres import get_postgres_provider
from src.app.db.redis import get_redis_provider

logging.basicConfig(level=settings.APP_LOG_LEVEL)
logger = logging.getLogger(__name__)

routers = [
    ping_router,
    auth_router,
]


def create_app(test: bool) -> FastAPI:
    postgres_pr = get_postgres_provider(test=test)
    redis_pr = get_redis_provider(test=test)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # ---------- STARTUP ----------
        # Postgres init
        await postgres_pr.connect()

        # Redis init
        await redis_pr.connect()
        yield

        # ---------- SHUTDOWN ----------
        await postgres_pr.close()
        await redis_pr.disconnect()

    app: FastAPI = FastAPI(
        title=settings.PROJECT_NAME,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    # ---------- State ----------
    app.state.testing = test  # test mode flag
    for router in routers:
        app.include_router(router)
    return app
