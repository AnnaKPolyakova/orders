from collections.abc import Callable
from typing import Any, cast

from fastapi import Request
from fastapi_users.authentication import Strategy
from fastapi_users.db import SQLAlchemyUserDatabase
from loguru import logger
from src.app.db.postgres import get_postgres_provider
from src.app.models.db_models import User
from src.app.services.users import UserManager, auth_backend
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and set user in request.state"""

    async def dispatch(self, request: Request, call_next: Callable) -> Any:  # type: ignore[type-arg]
        # Try to get user from token
        user: User | None = None
        try:
            # Get token from Authorization header
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
                strategy: Strategy[User, int] = cast(
                    Strategy[Any, Any], auth_backend.get_strategy()
                )

                # Get user manager
                pg_provider = get_postgres_provider()
                if pg_provider.async_session_maker:
                    async with pg_provider.async_session_maker() as session:
                        user_db: SQLAlchemyUserDatabase[User, int] = (
                            SQLAlchemyUserDatabase(session, User)
                        )
                        user_manager = UserManager(user_db)
                        user = await strategy.read_token(token, user_manager)
        except Exception as e:
            # If token is invalid or missing, just continue without user
            logger.debug("Failed to get user from token: %s", e)

        # Set user in request.state
        request.state.user = user

        response = await call_next(request)
        return response
