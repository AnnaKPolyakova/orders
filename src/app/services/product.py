import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.postgres import get_async_db_session
from src.app.models.db_models.catalog import CatalogItem
from src.app.models.db_models.product import Product
from src.app.models.db_models.product_history import (
    ProductAction,
    ProductHistory,
)
from src.app.models.validators.product import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
)

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _create_product_snapshot(self, product: Product) -> dict[str, Any]:
        """Create snapshot of product data for history"""
        # return {
        #     "id": product.id,
        #     "catalog_item_id": product.catalog_item_id,
        #     "sell_price": float(product.sell_price) if product.sell_price else None,
        #     "purchase_price": (
        #         float(product.purchase_price) if product.purchase_price else None
        #     ),
        #     "created_at": product.created_at.isoformat() if product.created_at else None,
        #     # "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        # }
        json_data = ProductRead.model_validate(product).model_dump(mode="json")
        return json_data

    async def _save_history(
        self,
        product: Product,
        action: ProductAction,
        user_id: int | None = None,
    ) -> None:
        """Save product change to history"""
        snapshot = self._create_product_snapshot(product)

        # For UPDATE action, check if snapshot changed compared to last history
        if action == ProductAction.UPDATED:
            last_history_query = (
                select(ProductHistory)
                .where(ProductHistory.product_id == product.id)
                .order_by(ProductHistory.created_at.desc())
                .limit(1)
            )
            last_history_result = await self.session.execute(
                last_history_query
            )
            last_history = last_history_result.scalar_one_or_none()

            # Skip saving if snapshot hasn't changed
            if last_history is not None and last_history.snapshot == snapshot:
                return

        history_record = ProductHistory(
            product_id=product.id,
            user_id=user_id,
            action=action.value,
            snapshot=snapshot,
        )
        self.session.add(history_record)

    async def get_products(self) -> list[Product]:
        # Get items
        query = select(Product).order_by(Product.id)
        result = await self.session.execute(query)
        items = list(result.scalars().all())
        return items

    async def get_product(self, product_id: int) -> Product:
        """Get single product by id"""
        query = select(Product).where(Product.id == product_id)
        result = await self.session.execute(query)
        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )

        return product

    async def create_product(
        self, product_data: ProductCreate, user_id: int | None = None
    ) -> Product:
        """Create new product"""
        # Verify catalog_item_id exists
        catalog_query = select(CatalogItem).where(
            CatalogItem.id == product_data.catalog_item_id
        )
        catalog_result = await self.session.execute(catalog_query)
        catalog_item = catalog_result.scalar_one_or_none()

        if catalog_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog item with id {product_data.catalog_item_id} not found",
            )

        new_product = Product(
            catalog_item_id=product_data.catalog_item_id,
            sell_price=product_data.sell_price,
            purchase_price=product_data.purchase_price,
            quantity=product_data.quantity,
        )
        self.session.add(new_product)
        await self.session.flush()  # Flush to get product.id
        await self._save_history(new_product, ProductAction.CREATED, user_id)
        await self.session.commit()
        return new_product

    async def update_product(
        self,
        product_id: int,
        product_data: ProductUpdate,
        user_id: int | None = None,
    ) -> Product:
        """Update existing product"""
        product = await self.get_product(product_id)

        if product_data.catalog_item_id is not None:
            catalog_query = select(CatalogItem).where(
                CatalogItem.id == product_data.catalog_item_id
            )
            catalog_result = await self.session.execute(catalog_query)
            catalog_item = catalog_result.scalar_one_or_none()

            if catalog_item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog item with id {product_data.catalog_item_id} not found",
                )
            product.catalog_item_id = product_data.catalog_item_id

        for field, value in product_data.model_dump(
            exclude_unset=True
        ).items():
            setattr(product, field, value)
        await self.session.flush()  # Flush to get updated values
        await self.session.refresh(product)
        await self._save_history(product, ProductAction.UPDATED, user_id)
        await self.session.commit()
        return product


async def get_product_service(
    session: AsyncSession = Depends(get_async_db_session),
) -> AsyncGenerator[ProductService]:
    yield ProductService(session)
