from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.models.db_models import Order, OrderItem, Product, User
from src.app.models.db_models.order import PaymentStatus

from tests.conftest import ERROR_INFO


@pytest.mark.asyncio
async def test_create_order_success(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    user: User,
    product: Product,
    access_token: str,
) -> None:
    url = "/orders"
    method = "post"
    item_data = {
        "product_id": product.id,
        "quantity": 2,
    }
    payload = {"items": [item_data]}
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.CREATED, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.CREATED
    )
    assert data["id"] is not None
    assert data["user_id"] == user.id
    assert data["payment_status"] == PaymentStatus.UNPAID.value
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id
    assert data["items"][0]["quantity"] == item_data["quantity"]

    # Check that order item stored snapshot price
    db_items = await db_session.execute(
        select(OrderItem).where(OrderItem.order_id == data["id"])
    )
    order_item = db_items.scalar_one()
    assert float(order_item.price) == float(product.sell_price)


@pytest.mark.asyncio
async def test_create_order_product_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    url = "/orders"
    method = "post"
    payload = {
        "items": [
            {
                "product_id": 999999,
                "quantity": 1,
            }
        ]
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_get_order_success(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    user: User,
    product: Product,
    access_token: str,
) -> None:
    # Create order directly via API
    create_response = await async_client.post(
        "/orders",
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                }
            ]
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    order_data = create_response.json()

    url = f"/orders/{order_data['id']}"
    method = "get"

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == order_data["id"]
    assert data["user_id"] == user.id
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id


@pytest.mark.asyncio
async def test_get_order_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    url = "/orders/999999"
    method = "get"

    response = await getattr(async_client, method)(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_update_order_items(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    order: Order,
    access_token: str,
) -> None:
    # use order from fixture
    item_id = order.items[0].id
    order_itmes_count = len(order.items)
    url = f"/orders/{order.id}"
    method = "patch"
    payload = {
        "delete_item_ids": [],
        "new_items": [],
        "update_items": [
            {
                "item_id": item_id,
                "quantity": 3,
            }
        ],
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == order.id
    assert len(data["items"]) == order_itmes_count


@pytest.mark.asyncio
async def test_update_order_add_and_delete_items(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    order: Order,
    access_token: str,
) -> None:
    # use order from fixture
    product_id = order.items[0].product_id

    url = f"/orders/{order.id}"
    method = "patch"
    payload = {
        "delete_item_ids": [order.items[0].id],
        "new_items": [
            {
                "product_id": product_id,
                "quantity": 5,
            }
        ],
        "update_items": [],
    }
    order_items_count = len(order.items)
    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == order.id
    assert len(data["items"]) == order_items_count


@pytest.mark.asyncio
async def test_update_order_not_found(
    async_client: httpx.AsyncClient,
    access_token: str,
) -> None:
    url = "/orders/999999"
    method = "patch"
    payload = {
        "delete_item_ids": [1],
        "new_items": [],
        "update_items": [],
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.NOT_FOUND
    )


@pytest.mark.asyncio
async def test_update_order_payment_status(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    product: Product,
    access_token: str,
    order: Order,
) -> None:
    url = f"/orders/{order.id}/payment-status"
    method = "patch"
    payload = {
        "payment_status": PaymentStatus.PAID.value,
    }

    response = await getattr(async_client, method)(
        url, json=payload, headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK, ERROR_INFO.format(
        method=method, url=url, status=HTTPStatus.OK
    )
    assert data["id"] == order.id
    assert data["payment_status"] == PaymentStatus.PAID.value


@pytest.mark.asyncio
async def test_update_order_payment_status_invalid(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    product: Product,
    access_token: str,
    order: Order,
) -> None:
    url = f"/orders/{order.id}/payment-status"
    method = "patch"
    payload = {
        "payment_status": "unknown",
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
