import logging
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

logger = logging.getLogger(__name__)


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
        new_order = Order(user_id=user_id)
        self.session.add(new_order)
        await self.session.flush()

        # Create items based on provided products
        for item_data in order_data.items:
            product = await self._get_product_or_404(item_data.product_id)
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=item_data.quantity,
                price=float(product.sell_price),
            )
            self.session.add(order_item)

        await self.session.commit()
        await self.session.refresh(new_order)
        return await self.get_order(new_order.id)

    async def update_order(
        self, order_id: int, order_data: OrderUpdate
    ) -> Order:
        """Update order items:

        - delete only items with products in delete_product_ids
        - add only items from new_items
        - update only items from update_items
        """
        order = await self.get_order(order_id)

        items_by_id: dict[int, OrderItem] = {
            item.id: item for item in order.items
        }

        # Delete specific order items by item_id
        if order_data.delete_item_ids:
            for item_id in order_data.delete_item_ids:
                item = items_by_id.get(item_id)
                if item is not None:
                    await self.session.delete(item)

        # Update existing items (by item_id)
        if order_data.update_items:
            for update in order_data.update_items:
                item = items_by_id.get(update.item_id)
                if item is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=(
                            f"Order item with id {update.item_id} "
                            f"not found in order {order.id}"
                        ),
                    )
                item.quantity = update.quantity

        # Add new items
        if order_data.new_items:
            for item_data in order_data.new_items:
                product = await self._get_product_or_404(item_data.product_id)
                new_item = OrderItem(
                    order=order,
                    product=product,
                    quantity=item_data.quantity,
                    price=float(product.sell_price),
                )
                self.session.add(new_item)

        await self.session.commit()
        await self.session.refresh(order)  # обновляем identity map
        return await self.get_order(order.id)

    async def update_payment_status(
        self,
        order_id: int,
        payment_update: OrderPaymentUpdate,
        user: User,
    ) -> Order:
        """Update payment status of order with proper locking"""
        # 1️⃣ Получаем order с items и продуктами с блокировкой
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order_id)
            .with_for_update()  # блокировка
        )
        order = await self.session.scalar(stmt)
        if not order:
            raise HTTPException(404, "Order not found")

        # 2️⃣ Проверяем количество
        for item in order.items:
            if item.quantity > item.product.quantity:
                raise HTTPException(
                    400,
                    f"Недостаточно товара на складе: product_id={item.product.id}",
                )

        # 3️⃣ Уменьшаем количество через сервис
        for item in order.items:
            product_data: dict[str, Any] = {
                "quantity": item.product.quantity - item.quantity
            }
            await self.product_service.update_product(
                item.product.id,
                ProductUpdate(**product_data),
                user_id=user.id,
            )

        # 4️⃣ Обновляем статус оплаты
        order.payment_status = payment_update.payment_status.value

        # 5️⃣ Коммитим
        await self.session.commit()

        # 6️⃣ Возвращаем актуальный order
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
