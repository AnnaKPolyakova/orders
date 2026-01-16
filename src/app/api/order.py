from fastapi import APIRouter, Depends, Request

from src.app.api.auth import fastapi_users
from src.app.models.db_models import Order
from src.app.models.validators.order import (
    OrderCreate,
    OrderPaymentUpdate,
    OrderRead,
    OrderUpdate,
)
from src.app.services.order import OrderService, get_order_service

order_router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(fastapi_users.current_user(active=True))],
)


@order_router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    request: Request,
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Get single order by id"""
    order = await service.get_order(order_id)
    return order


@order_router.post("", response_model=OrderRead, status_code=201)
async def create_order(
    request: Request,
    order_data: OrderCreate,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Create new order for current user"""
    order = await service.create_order(
        order_data, user_id=request.state.user.id
    )
    return order


@order_router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    request: Request,
    order_id: int,
    order_data: OrderUpdate,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Update existing order"""
    order = await service.update_order(order_id, order_data)
    return order


@order_router.patch("/{order_id}/payment-status", response_model=OrderRead)
async def update_order_payment_status(
    request: Request,
    order_id: int,
    payment_update: OrderPaymentUpdate,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Update payment status of order"""
    order = await service.update_payment_status(
        order_id, payment_update, request.state.user
    )
    return order
