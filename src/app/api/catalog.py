from typing import Any

from fastapi import APIRouter, Depends, Request

from src.app.api.auth import fastapi_users
from src.app.models.db_models import CatalogItem
from src.app.models.validators.catalog import (
    CatalogItemCreate,
    CatalogItemListResponse,
    CatalogItemRead,
    CatalogItemUpdate,
)
from src.app.services.catalog import CatalogService, get_catalog_service
from src.app.services.pagination import (
    PaginationService,
    get_pagination_service,
)

catalog_router = APIRouter(
    prefix="/catalog",
    tags=["catalog"],
    dependencies=[Depends(fastapi_users.current_user(active=True))],
)


@catalog_router.get("", response_model=CatalogItemListResponse)
async def get_catalog_items(
    request: Request,
    service: CatalogService = Depends(get_catalog_service),
    pagination_service: PaginationService = Depends(get_pagination_service),
) -> dict[str, Any]:
    """Get paginated list of catalog items"""
    items = await service.get_catalog_items()
    return pagination_service.build_paginated_response(items)


@catalog_router.get("/{item_id}", response_model=CatalogItemRead)
async def get_catalog_item(
    request: Request,
    item_id: int,
    service: CatalogService = Depends(get_catalog_service),
) -> CatalogItem:
    """Get single catalog item by id"""
    item = await service.get_catalog_item(item_id)
    return item


@catalog_router.post("", response_model=CatalogItemRead, status_code=201)
async def create_catalog_item(
    request: Request,
    item_data: CatalogItemCreate,
    service: CatalogService = Depends(get_catalog_service),
) -> CatalogItem:
    """Create new catalog item"""
    item = await service.create_catalog_item(item_data)
    return item


@catalog_router.patch("/{item_id}", response_model=CatalogItemRead)
async def update_catalog_item(
    request: Request,
    item_id: int,
    item_data: CatalogItemUpdate,
    service: CatalogService = Depends(get_catalog_service),
) -> CatalogItem:
    """Update existing catalog item"""
    item = await service.update_catalog_item(item_id, item_data)
    return item
