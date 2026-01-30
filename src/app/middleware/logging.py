import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Any:  # type: ignore[type-arg]
        # Get user from request.state (set by AuthMiddleware)
        user = getattr(request.state, "user", None)
        user_id = user.id if user else None
        data: str | dict = ""  # type: ignore[type-arg]
        try:
            content_type = request.headers.get("content-type", "").lower()
            # Check if it's form-data
            if "multipart/form-data" in content_type:
                # Parse multipart/form-data
                try:
                    body = await request.body()
                    data = body.decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.debug("Failed to parse multipart: %s", e)
            else:
                try:
                    body = await request.body()
                    data = json.loads(body)
                except Exception as e:
                    logger.debug("Failed to parse json: %s", e)
        except Exception as e:
            logger.debug("Failed to parse data: %s", e)
        if "password" not in data:  # noqa: SIM108
            data = str(body)
        else:
            data = "sensitive data"
        # Log request
        logger.info(
            "\nuser=%s,\ndata=%s,\nparams=%s,\napi=%s,\nmetjod=%s",
            user_id,
            data,
            dict(request.query_params),
            request.url.path,
            request.method,
        )
        response = await call_next(request)
        return response
