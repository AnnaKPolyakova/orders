from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.db.postgres import get_async_db_session
from src.app.models.db_models import Order, OrderItem, Product, User
from src.app.models.validators.order import (
    OrderCreate,
    OrderPaymentUpdate,
    OrderUpdate,
)
from src.app.models.validators.product import ProductUpdate
from src.app.services import ProductService


class OrderService:
    """Service for order operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_service = ProductService(session)

    async def get_order(self, order_id: int) -> Order:
        """Get single order by id with items"""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )

        order = await self.session.scalar(stmt)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with id {order_id} not found",
            )

        return order

    async def create_order(
        self, order_data: OrderCreate, user_id: int
    ) -> Order:
        """Create new order with items for user"""
        new_order = await self._create_order_record(user_id)
        await self._add_items_to_order(new_order, order_data.items)
        await self.session.commit()
        await self.session.refresh(new_order)
        return await self.get_order(new_order.id)

    async def _create_order_record(self, user_id: int) -> Order:
        """Create and flush new order record"""
        new_order = Order(user_id=user_id)
        self.session.add(new_order)
        await self.session.flush()
        return new_order

    async def _add_items_to_order(
        self, order: Order, items_data: list[Any]
    ) -> None:
        """Add order items to order"""
        for item_data in items_data:
            order_item = await self._create_order_item(order, item_data)
            self.session.add(order_item)

    async def _create_order_item(
        self, order: Order, item_data: Any
    ) -> OrderItem:
        """Create order item from item data"""
        product = await self._get_product_or_404(item_data.product_id)
        return OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item_data.quantity,
            price=float(product.sell_price),
        )

    async def update_order(
        self, order_id: int, order_data: OrderUpdate
    ) -> Order:
        """Update order items:

        - delete only items with products in delete_product_ids
        - add only items from new_items
        - update only items from update_items
        """
        order = await self.get_order(order_id)
        items_by_id = self._build_items_map(order.items)

        if order_data.delete_item_ids:
            await self._delete_order_items(
                items_by_id, order_data.delete_item_ids
            )

        if order_data.update_items:
            await self._update_order_items(
                items_by_id, order_data.update_items, order.id
            )

        if order_data.new_items:
            await self._add_new_items_to_order(order, order_data.new_items)

        await self.session.commit()
        await self.session.refresh(order)  # обновляем identity map
        return await self.get_order(order.id)

    def _build_items_map(self, items: list[OrderItem]) -> dict[int, OrderItem]:
        """Build dictionary mapping item id to OrderItem"""
        return {item.id: item for item in items}

    async def _delete_order_items(
        self, items_by_id: dict[int, OrderItem], item_ids: list[int]
    ) -> None:
        """Delete order items by their ids"""
        for item_id in item_ids:
            item = items_by_id.get(item_id)
            if item is not None:
                await self.session.delete(item)

    async def _update_order_items(
        self,
        items_by_id: dict[int, OrderItem],
        update_items: list[Any],
        order_id: int,
    ) -> None:
        """Update existing order items quantities"""
        for update in update_items:
            item = items_by_id.get(update.item_id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Order item with id {update.item_id} "
                        f"not found in order {order_id}"
                    ),
                )
            item.quantity = update.quantity

    async def _add_new_items_to_order(
        self, order: Order, new_items: list[Any]
    ) -> None:
        """Add new items to existing order"""
        for item_data in new_items:
            product = await self._get_product_or_404(item_data.product_id)
            new_item = OrderItem(
                order=order,
                product=product,
                quantity=item_data.quantity,
                price=float(product.sell_price),
            )
            self.session.add(new_item)

    async def update_payment_status(
        self,
        order_id: int,
        payment_update: OrderPaymentUpdate,
        user: User,
    ) -> Order:
        """Update payment status of order with proper locking"""
        order = await self._get_order_with_lock(order_id)
        await self._validate_stock_availability(order.items)
        await self._reduce_product_quantities(order.items, user.id)
        order.payment_status = payment_update.payment_status.value
        await self.session.commit()
        return await self._get_order_with_items(order_id)

    async def _get_order_with_lock(self, order_id: int) -> Order:
        """Get order with items and products with row-level lock"""
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order_id)
            .with_for_update()  # блокировка
        )
        order = await self.session.scalar(stmt)
        if not order:
            raise HTTPException(404, "Order not found")
        return order

    async def _validate_stock_availability(
        self, items: list[OrderItem]
    ) -> None:
        """Validate that there is enough stock for all order items"""
        for item in items:
            if item.quantity > item.product.quantity:
                raise HTTPException(
                    400,
                    f"Недостаточно товара на складе: product_id={item.product.id}",
                )

    async def _reduce_product_quantities(
        self, items: list[OrderItem], user_id: int
    ) -> None:
        """Reduce product quantities based on order items"""
        for item in items:
            product_data: dict[str, Any] = {
                "quantity": item.product.quantity - item.quantity
            }
            await self.product_service.update_product(
                item.product.id,
                ProductUpdate(**product_data),
                user_id=user_id,
            )

    async def _get_order_with_items(self, order_id: int) -> Order:
        """Get order with items and products loaded"""
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order_id)
        )
        return await self.session.scalar(stmt)  # type: ignore[return-value]

    async def _get_product_or_404(self, product_id: int) -> Product:
        query = select(Product).where(Product.id == product_id)
        result = await self.session.execute(query)
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )
        return product


async def get_order_service(
    session: AsyncSession = Depends(get_async_db_session),
) -> AsyncGenerator[OrderService]:
    yield OrderService(session)
