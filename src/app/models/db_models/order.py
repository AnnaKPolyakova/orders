from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.db_models.base import BaseFields
from src.app.models.db_models.user import User

if TYPE_CHECKING:
    from src.app.models.db_models.order_item import OrderItem


class PaymentStatus(str, enum.Enum):
    """Payment status for orders."""

    UNPAID = "unpaid"
    PAID = "paid"
    CANCELED = "canceled"


class Order(BaseFields):
    __tablename__ = "order"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    payment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.UNPAID.value,
    )
    user: Mapped[User] = relationship("User", back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
