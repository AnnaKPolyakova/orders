from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.models.db_models import CatalogItem, Product

from tests.conftest import ERROR_INFO, settings


@pytest.mark.asyncio
async def test_get_products_default_pagination(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    products: list[Product],
    access_token: str,
) -> None:
    url = "/products"
    method = "get"
    products_count = await db_session.execute(
        select(func.count()).select_from(Product)
    )
    total_products = products_count.scalar_one()

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert len(data["items"]) == settings.PAGE_SIZE
    assert data["total"] == total_products
    assert data["page"] == 1
    assert data["page_size"] == settings.PAGE_SIZE
    assert data["prev_page"] is None
    assert data["next_page"] == (
        "http://test/products?page=2&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)


@pytest.mark.asyncio
async def test_get_products_with_pagination(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    products: list[Product],
    access_token: str,
) -> None:
    page = 2
    url = "/products?page={page}&page_size={page_size}".format(
        page=page, page_size=settings.PAGE_SIZE
    )
    method = "get"
    products_count = await db_session.execute(
        select(func.count()).select_from(Product)
    )
    total_products = products_count.scalar_one()

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert len(data["items"]) == settings.PAGE_SIZE
    assert data["total"] == total_products
    assert data["page"] == page
    assert data["page_size"] == settings.PAGE_SIZE
    assert data["prev_page"] == (
        "http://test/products?page=1&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)
    assert data["next_page"] == (
        "http://test/products?page=3&page_size={page_size}"
    ).format(page_size=settings.PAGE_SIZE)


@pytest.mark.asyncio
async def test_get_product_success(
    async_client: httpx.AsyncClient,
    product: Product,
    access_token: str,
) -> None:
    url = f"/products/{product.id}"
    method = "get"

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == product.id
    assert data["catalog_item_id"] == product.catalog_item_id
    assert data["sell_price"] == float(product.sell_price)
    assert data["purchase_price"] == float(product.purchase_price)


@pytest.mark.asyncio
async def test_get_product_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    url = "/products/99999"
    method = "get"

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_create_product_success(
    async_client: httpx.AsyncClient,
    catalog_item: CatalogItem,
    access_token: str,
) -> None:
    url = "/products"
    method = "post"
    payload = {
        "catalog_item_id": catalog_item.id,
        "sell_price": 199.99,
        "purchase_price": 149.99,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.CREATED, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.CREATED
    )
    assert data["id"] is not None
    assert data["catalog_item_id"] == payload["catalog_item_id"]
    assert data["sell_price"] == payload["sell_price"]
    assert data["purchase_price"] == payload["purchase_price"]
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_product_catalog_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    url = "/products"
    method = "post"
    payload = {
        "catalog_item_id": 99999,
        "sell_price": 100.0,
        "purchase_price": 50.0,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_create_product_invalid_data(
    async_client: httpx.AsyncClient,
    catalog_item: CatalogItem,
    access_token: str,
) -> None:
    url = "/products"
    method = "post"
    payload = {
        "catalog_item_id": catalog_item.id,
        "sell_price": -1,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        ERROR_INFO.format(
            method=method, url=url, status=HTTPStatus.UNPROCESSABLE_ENTITY
        )
    )


@pytest.mark.asyncio
async def test_update_product(
    async_client: httpx.AsyncClient,
    product: Product,
    access_token: str,
) -> None:
    url = f"/products/{product.id}"
    method = "patch"
    payload = {
        "sell_price": 250.0,
        "purchase_price": 200.0,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == product.id
    assert data["sell_price"] == payload["sell_price"]
    assert data["purchase_price"] == payload["purchase_price"]
    assert data["catalog_item_id"] == product.catalog_item_id


@pytest.mark.asyncio
async def test_update_product_partial(
    async_client: httpx.AsyncClient,
    product: Product,
    access_token: str,
) -> None:
    url = f"/products/{product.id}"
    method = "patch"
    payload = {
        "sell_price": 300.5,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == product.id
    assert data["sell_price"] == payload["sell_price"]
    assert data["purchase_price"] == float(product.purchase_price)
    assert data["catalog_item_id"] == product.catalog_item_id


@pytest.mark.asyncio
async def test_update_product_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    url = "/products/99999"
    method = "patch"
    payload = {
        "sell_price": 123.45,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_update_product_catalog_not_found(
    async_client: httpx.AsyncClient,
    product: Product,
    access_token: str,
) -> None:
    url = f"/products/{product.id}"
    method = "patch"
    payload = {
        "catalog_item_id": 99999,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )
