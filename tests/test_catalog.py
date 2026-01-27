from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.models.db_models import CatalogItem

from tests.conftest import ERROR_INFO, settings


@pytest.mark.asyncio
async def test_get_catalog_items_with_pagination(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    catalog_items: list[CatalogItem],
    access_token: str,
) -> None:
    """Test getting catalog items with pagination."""
    # Test second page
    url = "/catalog?page=1&page_size={page_size}".format(
        page_size=settings.PAGE_SIZE
    )
    method = "get"
    catalogs = await db_session.execute(
        select(func.count()).select_from(CatalogItem)
    )
    catalogs_count = catalogs.scalar_one()
    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()
    assert response.status_code == HTTPStatus.OK
    assert len(data["items"]) == settings.PAGE_SIZE
    assert data["total"] == catalogs_count
    assert data["page"] == 1
    assert data["page_size"] == settings.PAGE_SIZE
    assert data["prev_page"] is None
    assert data["next_page"] == (
        "http://test/catalog?page=2&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)


@pytest.mark.asyncio
async def test_get_catalog_item_success(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    catalog_item: CatalogItem,
    access_token: str,
) -> None:
    """Test getting single catalog item."""

    url = f"/catalog/{catalog_item.id}"
    method = "get"

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == catalog_item.id
    assert data["name"] == catalog_item.name
    assert data["description"] == catalog_item.description


@pytest.mark.asyncio
async def test_get_catalog_item_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    """Test getting non-existent catalog item."""
    url = "/catalog/99999"
    method = "get"
    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_create_catalog_item(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    """Test creating new catalog item."""
    url = "/catalog"
    method = "post"
    payload = {
        "name": "Test Product",
        "description": "Test Description",
    }
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.CREATED, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.CREATED
    )
    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_catalog_item_without_description(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    """Test creating catalog item without description."""
    url = "/catalog"
    method = "post"
    payload = {
        "name": "Test Product",
    }
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.CREATED, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.CREATED
    )
    assert data["name"] == payload["name"]
    assert data["description"] is None


@pytest.mark.asyncio
async def test_create_catalog_item_invalid_data(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    """Test creating catalog item with invalid data."""
    url = "/catalog"
    method = "post"
    # Missing required field 'name'
    payload = {
        "description": "Test Description",
    }
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        ERROR_INFO.format(
            method=method,
            url=url,
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    )


@pytest.mark.asyncio
async def test_update_catalog_item(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    catalog_item: CatalogItem,
    access_token: str,
) -> None:
    """Test updating catalog item."""

    url = f"/catalog/{catalog_item.id}"
    method = "patch"
    payload = {
        "name": "Updated Name",
        "description": "Updated Description",
    }
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == catalog_item.id
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]


@pytest.mark.asyncio
async def test_update_catalog_item_partial(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    catalog_item: CatalogItem,
    access_token: str,
) -> None:
    """Test partial update of catalog item."""

    url = f"/catalog/{catalog_item.id}"
    method = "patch"
    # Update only name
    payload = {
        "name": "Updated Name",
    }
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["name"] == payload["name"]
    assert data["description"] == catalog_item.description
    # Should remain unchanged


@pytest.mark.asyncio
async def test_update_catalog_item_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    """Test updating non-existent catalog item."""
    url = "/catalog/99999"
    method = "patch"
    payload = {
        "name": "Updated Name",
    }
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_get_catalog_items_default_pagination(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    catalog_items: list[CatalogItem],
    access_token: str,
) -> None:
    """Test getting catalog items with default pagination."""
    url = "/catalog"
    method = "get"
    catalogs = await db_session.execute(
        select(func.count()).select_from(CatalogItem)
    )
    catalogs_count = catalogs.scalar_one()

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert len(data["items"]) == settings.PAGE_SIZE
    assert data["total"] == catalogs_count
    assert data["page"] == 1
    assert "page_size" in data
    assert data["prev_page"] is None
    assert data["next_page"] == (
        "http://test/catalog?page=2&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)


@pytest.mark.asyncio
async def test_get_catalog_items_middle_page(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    catalog_items: list[CatalogItem],
    access_token: str,
) -> None:
    """Test getting catalog items from middle page."""

    page = 2
    url = "/catalog?page={page}&page_size={page_size}".format(
        page=page, page_size=settings.PAGE_SIZE
    )
    method = "get"
    catalogs = await db_session.execute(
        select(func.count()).select_from(CatalogItem)
    )
    catalogs_count = catalogs.scalar_one()

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert len(data["items"]) == settings.PAGE_SIZE
    assert data["total"] == catalogs_count
    assert data["page"] == page
    assert data["page_size"] == settings.PAGE_SIZE
    assert data["prev_page"] == (
        "http://test/catalog?page=1&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)
    assert data["next_page"] == (
        "http://test/catalog?page=3&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)
