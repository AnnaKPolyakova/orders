import logging
from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Depends, Response, status
from fastapi_users import BaseUserManager, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    Authenticator,
    BearerTransport,
    CookieTransport,
    Strategy,
)
from fastapi_users.authentication.strategy import (
    StrategyDestroyNotSupportedError,
)
from fastapi_users.authentication.strategy.jwt import JWTStrategy
from fastapi_users.authentication.transport import (
    TransportLogoutNotSupportedError,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.models import ID, UP

# from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from src.app.core.config import settings
from src.app.db.postgres import get_async_db_session, get_postgres_provider
from src.app.models.db_models import RevokedToken, User

logger = logging.getLogger(__name__)


class BlacklistJWTStrategy(JWTStrategy[UP, ID]):
    async def read_token(
        self,
        token: str | None,
        user_manager: BaseUserManager[models.UP, models.ID],
    ) -> models.UP | None:
        pg_provider = get_postgres_provider()
        if pg_provider.async_session_maker is None:
            return None
        async with pg_provider.async_session_maker() as session:
            result = await session.execute(
                select(RevokedToken).where(RevokedToken.token == token)
            )
            revoked = result.scalar_one_or_none()
            if revoked:
                return None
        return await super().read_token(token, user_manager)

    async def destroy_token(self, token: str, user: UP) -> None:
        pg_provider = get_postgres_provider()
        if pg_provider.async_session_maker is None:
            return
        async with pg_provider.async_session_maker() as session:
            result = await session.execute(
                select(RevokedToken).where(RevokedToken.token == token)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return
            revoked = RevokedToken(token=token, user_id=user.id)
            session.add(revoked)
            await session.commit()


async def get_user_db(
    session: AsyncSession = Depends(get_async_db_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, int]]:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(BaseUserManager[models.UP, int]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    def parse_id(self, id: str) -> int:
        return int(id)

    async def get_logout_response(self) -> Response:
        raise TransportLogoutNotSupportedError()


class AuthBackendWithRefresh(AuthenticationBackend[models.UP, models.ID]):
    async def login(self, strategy: Strategy[UP, ID], user: UP) -> Response:
        token = await strategy.write_token(user)
        strategy = get_refresh_strategy()
        refresh_token: str = await strategy.write_token(user)
        response = await self.transport.get_login_response(token)
        transport = cast(CookieTransportCustom, refresh_backend.transport)
        await transport.set_login_cookie(response, refresh_token)
        return response

    async def logout(
        self,
        strategy: Strategy[UP, ID],
        user: UP,
        token: str,
    ) -> Response:
        try:
            await strategy.destroy_token(token, user)
        except StrategyDestroyNotSupportedError:
            logger.info("Strategy DestroyNotSupportedError")
        try:
            response = await self.transport.get_logout_response()
        except TransportLogoutNotSupportedError:
            response = Response(status_code=status.HTTP_204_NO_CONTENT)
        return response


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, int] = Depends(get_user_db),
) -> AsyncGenerator[UserManager[User]]:
    yield UserManager(user_db)


def get_jwt_strategy() -> BlacklistJWTStrategy[UP, ID]:
    return BlacklistJWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=900,  # 15 минут
        token_audience=["fastapi-users:auth"],
    )


def get_refresh_strategy() -> BlacklistJWTStrategy[UP, ID]:
    return BlacklistJWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=60 * 60 * 24 * 7,  # 7 дней
        token_audience=["fastapi-users:refresh"],
    )


class BearerTransportCustom(BearerTransport):
    async def get_logout_response(self) -> Response:
        return JSONResponse({"detail": "Logged out successfully"})


class CookieTransportCustom(CookieTransport):
    async def get_logout_response(self) -> Response:
        return JSONResponse({"detail": "Logged out successfully"})

    async def set_login_cookie(
        self, response: Response, refresh_token: str
    ) -> Response | None:
        if hasattr(self, "_set_login_cookie"):
            return self._set_login_cookie(response, refresh_token)
        return None


bearer_transport = BearerTransportCustom(tokenUrl="auth/jwt/login")
refresh_transport = CookieTransportCustom(
    cookie_name="refresh_token",
    cookie_secure=False,  # True на проде (HTTPS)
    cookie_httponly=False,  # JS не видит
    cookie_max_age=7 * 24 * 3600,  # 7 дней
)

auth_backend: AuthBackendWithRefresh[User, int] = AuthBackendWithRefresh(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

refresh_backend: AuthenticationBackend[User, int] = AuthenticationBackend(
    name="jwt-refresh",
    transport=refresh_transport,
    get_strategy=get_refresh_strategy,
)


authenticator = Authenticator(
    backends=[refresh_backend],
    get_user_manager=get_user_manager,
)
