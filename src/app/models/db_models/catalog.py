from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.db_models.base import BaseFields

if TYPE_CHECKING:
    from src.app.models.db_models.product import Product


class CatalogItem(BaseFields):
    """Catalog - list of available products"""

    __tablename__ = "catalog_item"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    products: Mapped[list[Product]] = relationship(
        "Product", back_populates="catalog_item"
    )
