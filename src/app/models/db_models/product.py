from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.db_models.base import BaseFields

if TYPE_CHECKING:
    from src.app.models.db_models.catalog import CatalogItem
    from src.app.models.db_models.order_item import OrderItem
    from src.app.models.db_models.product_history import ProductHistory


class Product(BaseFields):
    """Product with price, based on catalog item"""

    __tablename__ = "product"

    catalog_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("catalog_item.id"), nullable=False
    )
    sell_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Current product price

    purchase_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Current purchase price

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Product quantity

    catalog_item: Mapped[CatalogItem] = relationship(
        "CatalogItem", back_populates="products"
    )
    order_items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="product"
    )
    histories: Mapped[list[ProductHistory]] = relationship(
        "ProductHistory", back_populates="product"
    )
