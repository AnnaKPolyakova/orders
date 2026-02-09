from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.db_models.base import BaseFields

if TYPE_CHECKING:
    from src.app.models.db_models.product import Product
    from src.app.models.db_models.user import User


class ProductAction(str, enum.Enum):
    """Action types for product history"""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class ProductHistory(BaseFields):
    """History of product changes"""

    __tablename__ = "product_history"

    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # created, updated, deleted
    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # Full snapshot of product data at the time of change

    product: Mapped[Product | None] = relationship(
        "Product", back_populates="histories"
    )
    user: Mapped[User | None] = relationship(
        "User", back_populates="histories"
    )
