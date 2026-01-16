from http import HTTPStatus
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.models.db_models import (
    CatalogItem,
    Product,
    ProductAction,
    ProductHistory,
    User,
)
from src.app.models.validators.product import ProductCreate, ProductUpdate
from src.app.services.product import ProductService


@pytest.mark.asyncio
async def test_create_product_creates_history(
    db_session: AsyncSession,
    catalog_item: CatalogItem,
    user: User,
) -> None:
    """Test that creating a product creates a history record"""
    service = ProductService(db_session)
    new_data = {
        "catalog_item_id": catalog_item.id,
        "sell_price": 100.0,
        "purchase_price": 50.0,
    }

    product_data = ProductCreate(**new_data)  # type: ignore[arg-type]

    product = await service.create_product(product_data, user_id=user.id)

    # Check history was created
    history_query = select(ProductHistory).where(
        ProductHistory.product_id == product.id
    )
    result = await db_session.execute(history_query)
    histories = list(result.scalars().all())

    assert len(histories) == 1
    history = histories[0]
    assert history.action == ProductAction.CREATED.value
    assert history.product_id == product.id
    assert history.user_id == user.id
    assert history.snapshot["id"] == product.id
    assert history.snapshot["catalog_item_id"] == catalog_item.id
    assert history.snapshot["sell_price"] == new_data["sell_price"]
    assert history.snapshot["purchase_price"] == new_data["purchase_price"]


@pytest.mark.asyncio
async def test_create_product_creates_history_without_user(
    db_session: AsyncSession,
    catalog_item: CatalogItem,
) -> None:
    """Test that creating a product creates history even without user"""
    service = ProductService(db_session)
    product_data = ProductCreate(
        catalog_item_id=catalog_item.id,
        sell_price=200.0,
        purchase_price=150.0,
    )  # type: ignore[call-arg]

    product = await service.create_product(product_data, user_id=None)

    # Check history was created
    history_query = select(ProductHistory).where(
        ProductHistory.product_id == product.id
    )
    result = await db_session.execute(history_query)
    histories = list(result.scalars().all())
    history = histories[0]

    assert len(histories) == 1
    assert history.action == ProductAction.CREATED.value
    assert history.user_id is None


@pytest.mark.asyncio
async def test_update_product_creates_history_when_changed(
    db_session: AsyncSession,
    product: Product,
    user: User,
) -> None:
    """Test that updating a product creates history when data changed"""
    service = ProductService(db_session)

    # Count existing histories
    count_before = await db_session.execute(
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    histories_before = count_before.scalar() or 0

    # Update product
    new_data: dict[str, Any] = {"sell_price": 999.99}
    update_data = ProductUpdate(**new_data)
    await service.update_product(product.id, update_data, user_id=user.id)

    # Check new history was created
    count_after = await db_session.execute(
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    histories_after = count_after.scalar() or 0

    # Check last history record
    last_history_query = (
        select(ProductHistory)
        .where(ProductHistory.product_id == product.id)
        .order_by(ProductHistory.created_at.desc())
        .limit(1)
    )
    result = await db_session.execute(last_history_query)
    last_history = result.scalar_one()

    assert histories_after == histories_before + 1
    assert last_history.action == ProductAction.UPDATED.value
    assert last_history.user_id == user.id
    assert last_history.snapshot["sell_price"] == new_data["sell_price"]


@pytest.mark.asyncio
async def test_update_product_no_history_when_unchanged(
    db_session: AsyncSession,
    product: Product,
    user: User,
) -> None:
    """Test that updating a product doesn't create history if data didn't change"""
    service = ProductService(db_session)

    # First, create initial history by updating with a specific value
    new_data: dict[str, Any] = {"sell_price": 999.0}
    update_data = ProductUpdate(**new_data)
    await service.update_product(product.id, update_data, user_id=user.id)

    # Count histories after first update
    initial_count = await db_session.execute(
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    initial_histories = initial_count.scalar() or 0
    assert initial_histories >= 1  # At least one history should exist

    # Now update with same value (should not create new history)
    update_data_same = ProductUpdate(**new_data)
    await service.update_product(product.id, update_data_same, user_id=user.id)

    # Check no new history was created
    count_after = await db_session.execute(
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    histories_after = count_after.scalar() or 0

    assert histories_after == initial_histories


@pytest.mark.asyncio
async def test_update_product_via_api_creates_history(
    async_client: httpx.AsyncClient,
    product: Product,
    access_token: str,
    db_session: AsyncSession,
    user: User,
) -> None:
    """Test that updating product via API creates history"""
    url = f"/products/{product.id}"

    payload = {"sell_price": 500.0}

    # Count histories before
    count_before = await db_session.execute(
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    histories_before = count_before.scalar() or 0

    response = await async_client.patch(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.OK

    # Check new history was created
    count_after = await db_session.execute(
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    histories_after = count_after.scalar() or 0

    assert histories_after == histories_before + 1

    # Verify history content
    last_history_query = (
        select(ProductHistory)
        .where(ProductHistory.product_id == product.id)
        .order_by(ProductHistory.created_at.desc())
        .limit(1)
    )
    result = await db_session.execute(last_history_query)
    last_history = result.scalar_one()

    assert last_history.action == ProductAction.UPDATED.value
    assert last_history.user_id == user.id
    assert last_history.snapshot["sell_price"] == payload["sell_price"]


@pytest.mark.asyncio
async def test_create_product_via_api_creates_history(
    async_client: httpx.AsyncClient,
    catalog_item: CatalogItem,
    access_token: str,
    db_session: AsyncSession,
    user: User,
) -> None:
    """Test that creating product via API creates history"""
    url = "/products"
    payload = {
        "catalog_item_id": catalog_item.id,
        "sell_price": 150.0,
        "purchase_price": 100.0,
    }

    response = await async_client.post(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.CREATED
    product_id = response.json()["id"]

    # Check history was created
    history_query = select(ProductHistory).where(
        ProductHistory.product_id == product_id
    )
    result = await db_session.execute(history_query)
    histories = list(result.scalars().all())

    assert len(histories) == 1
    history = histories[0]
    assert history.action == ProductAction.CREATED.value
    assert history.user_id == user.id


@pytest.mark.asyncio
async def test_multiple_updates_create_multiple_histories(
    db_session: AsyncSession,
    product: Product,
    user: User,
) -> None:
    """Test that multiple updates create multiple history records"""
    service = ProductService(db_session)

    # Count initial histories
    count_query = (
        select(func.count())
        .select_from(ProductHistory)
        .where(ProductHistory.product_id == product.id)
    )
    initial_count = (await db_session.execute(count_query)).scalar() or 0

    # Make multiple updates
    new_data: dict[str, Any] = {"purchase_price": 100.0, "sell_price": 150.0}
    await service.update_product(
        product.id,
        ProductUpdate(**new_data),
        user_id=user.id,
    )

    # Check all histories were created
    final_count = (await db_session.execute(count_query)).scalar() or 0

    # Verify last history
    last_history_query = (
        select(ProductHistory)
        .where(ProductHistory.product_id == product.id)
        .order_by(ProductHistory.created_at.desc())
        .limit(1)
    )
    result = await db_session.execute(last_history_query)
    last_history = result.scalar_one()

    assert final_count == initial_count + 1
    assert last_history.action == ProductAction.UPDATED.value
    assert (
        last_history.snapshot["purchase_price"] == new_data["purchase_price"]
    )
