from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from src.app.api.auth import fastapi_users
from src.app.models.db_models import Product, User
from src.app.models.validators.product import (
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
)
from src.app.services.pagination import (
    PaginationService,
    get_pagination_service,
)
from src.app.services.product import ProductService, get_product_service

product_router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(fastapi_users.current_user(active=True))],
)


@product_router.get("", response_model=ProductListResponse)
async def get_products(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    service: ProductService = Depends(get_product_service),
    pagination_service: PaginationService = Depends(get_pagination_service),
) -> dict[str, Any]:
    """Get paginated list of products"""
    items, total = await service.get_products(page=page, page_size=page_size)

    return pagination_service.build_paginated_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        request=request,
    )


@product_router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    request: Request,
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> Product:
    """Get single product by id"""
    product = await service.get_product(product_id)
    return product


@product_router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    request: Request,
    product_data: ProductCreate,
    service: ProductService = Depends(get_product_service),
    user: User = Depends(fastapi_users.current_user(active=True)),
) -> Product:
    """Create new product"""
    product = await service.create_product(product_data, user_id=user.id)
    return product


@product_router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    request: Request,
    product_id: int,
    product_data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
    user: User = Depends(fastapi_users.current_user(active=True)),
) -> Product:
    """Update existing product"""
    product = await service.update_product(
        product_id, product_data, user_id=user.id
    )
    return product
