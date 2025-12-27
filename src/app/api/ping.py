from typing import Any

from fastapi import APIRouter, Depends

from src.app.services.ping import PingService, get_ping_service

ping_router = APIRouter(
    prefix="/ping",
    tags=["ping"],
)


@ping_router.get("")
async def ping(
    service: PingService = Depends(get_ping_service),
) -> dict[str, Any]:
    return await service.check_health()
