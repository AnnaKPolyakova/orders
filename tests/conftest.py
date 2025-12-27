from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import redis
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.app.core.config import Settings
from src.app.main import create_app
from src.app.models.db_models import Base

ERROR_INFO = "Error for method: {method}, url: {url}, status: {status}"
settings = Settings()


@pytest.fixture(scope="session", autouse=True)
async def postgres_db():
    """Создает тестовую БД, создает таблицы, удаляет БД после тестов."""
    # имя тестовой базы
    admin_engine = create_async_engine(
        settings.POSTGRES_URL, isolation_level="AUTOCOMMIT"
    )
    # 1. Подключаемся к postgres (администратор)
    async with admin_engine.connect() as conn:
        # Проверяем существование базы
        result = await conn.execute(
            text(
                "SELECT 1 FROM pg_database WHERE datname = :db_name"
            ).bindparams(db_name=settings.POSTGRES_TEST_DB)
        )
        exists = result.scalar() is not None
        if exists:
            await conn.execute(
                text(f"DROP DATABASE {settings.POSTGRES_TEST_DB}")
            )
        await conn.execute(
            text(f"CREATE DATABASE {settings.POSTGRES_TEST_DB}")
        )
        print(f"Test DB created: {settings.POSTGRES_TEST_DB}")

    # engine к тестовой базе
    test_db_url = settings.POSTGRES_TEST_URL
    async_engine = create_async_engine(test_db_url, future=True)

    # создаем таблицы
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Удаляем БД
    # 1. Закрываем engine и пул
    await async_engine.dispose()

    async with admin_engine.connect() as conn:
        # 2. Убиваем все коннекты
        await conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = :db_name AND pid <> pg_backend_pid();"
            ).bindparams(db_name=settings.POSTGRES_TEST_DB)
        )

        # 3. Дропаем БД
        await conn.execute(text(f"DROP DATABASE {settings.POSTGRES_TEST_DB}"))


@pytest.fixture(scope="session", autouse=True)
def redis_db() -> Generator[redis.Redis]:  # type: ignore[type-arg]
    pool = redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_TEST_DB,
        password=settings.REDIS_PASSWORD,
    )
    client = redis.Redis(connection_pool=pool)
    client.flushdb()

    yield client

    # Очистим после завершения всех тестов
    client.flushdb()


@pytest.fixture(scope="session")
async def test_app() -> FastAPI:
    app_instance = create_app(test=True)
    return app_instance


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient]:
    # LifespanManager гарантированно вызывает startup/shutdown
    async with LifespanManager(test_app):
        transport = ASGITransport(app=test_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client
