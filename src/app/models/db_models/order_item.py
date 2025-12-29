from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.db_models.base import BaseFields

if TYPE_CHECKING:
    from src.app.models.db_models.order import Order
    from src.app.models.db_models.product import Product


class OrderItem(BaseFields):
    """Items in an order"""

    __tablename__ = "order_item"

    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("order.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Price at the time of order (may differ from current product price)
    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Product] = relationship(
        "Product", back_populates="order_items"
    )
