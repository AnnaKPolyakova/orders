from typing import Any

from fastapi import Depends

from src.app.db.postgres import PgConnector, get_db
from src.app.db.redis import RedisClient, get_redis


class PingService:
    def __init__(
        self, redis_provider: RedisClient, postgres_provider: PgConnector
    ) -> None:
        self.redis: RedisClient = redis_provider
        self.postgres: PgConnector = postgres_provider

    async def check_health(self) -> dict[str, Any]:
        result = {}

        try:
            result["redis_ping"] = (
                "pong" if await self.redis.ping() else "fail"
            )
        except Exception as e:
            result["redis_error"] = str(e)

        try:
            result["postgres_ping"] = (
                "pong" if await self.postgres.ping() else "fail"
            )
        except Exception as e:
            result["postgres_error"] = str(e)

        return result


def get_ping_service(
    redis_pr: RedisClient = Depends(get_redis),
    postgres_pr: PgConnector = Depends(get_db),
) -> PingService:
    return PingService(redis_pr, postgres_pr)
