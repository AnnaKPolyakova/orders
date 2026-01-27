import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.db.postgres import get_async_db_session
from src.app.models.db_models.catalog import CatalogItem
from src.app.models.validators.catalog import (
    CatalogItemCreate,
    CatalogItemUpdate,
)

logger = logging.getLogger(__name__)


class CatalogService:
    """Service for catalog operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_catalog_items(
        self, page: int = 1, page_size: int = settings.PAGE_SIZE
    ) -> tuple[list[CatalogItem], int]:
        """Get paginated list of catalog items"""
        page = max(page, 1)
        if page_size < 1:
            page_size = 10

        offset = (page - 1) * page_size

        # Get total count
        count_query = select(func.count()).select_from(CatalogItem)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Get items
        query = (
            select(CatalogItem)
            .offset(offset)
            .limit(page_size)
            .order_by(CatalogItem.id)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_catalog_item(self, item_id: int) -> CatalogItem:
        """Get single catalog item by id"""
        query = select(CatalogItem).where(CatalogItem.id == item_id)
        result = await self.session.execute(query)
        item = result.scalar_one_or_none()

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog item with id {item_id} not found",
            )

        return item

    async def create_catalog_item(
        self, item_data: CatalogItemCreate
    ) -> CatalogItem:
        """Create new catalog item"""
        new_item = CatalogItem(
            name=item_data.name,
            description=item_data.description,
        )
        self.session.add(new_item)
        await self.session.commit()
        await self.session.refresh(new_item)
        return new_item

    async def update_catalog_item(
        self, item_id: int, item_data: CatalogItemUpdate
    ) -> CatalogItem:
        """Update existing catalog item"""
        item = await self.get_catalog_item(item_id)

        if item_data.name is not None:
            item.name = item_data.name
        if item_data.description is not None:
            item.description = item_data.description

        await self.session.commit()
        await self.session.refresh(item)
        return item


async def get_catalog_service(
    session: AsyncSession = Depends(get_async_db_session),
) -> AsyncGenerator[CatalogService]:
    yield CatalogService(session)
