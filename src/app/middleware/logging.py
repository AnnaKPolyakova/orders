from collections.abc import Callable
from typing import Any

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Any:  # type: ignore[type-arg]
        user = getattr(request.state, "user", None)
        logger.bind(
            user=getattr(user, "email", None),
            method=request.method,
            path=request.url.path,
        ).info("request")

        response = await call_next(request)
        return response
