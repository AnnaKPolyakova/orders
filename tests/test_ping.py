from http import HTTPStatus

import httpx
import pytest

from tests.conftest import ERROR_INFO


@pytest.mark.asyncio
async def test_ping_with_real_connections(
    async_client: httpx.AsyncClient,
) -> None:
    status = HTTPStatus.OK
    url = "/ping"
    method = "get"
    response = await getattr(async_client, method)(url)
    data = response.json()
    assert response.status_code == status, ERROR_INFO.format(
        method=method, url=url, status=status
    )
    assert isinstance(data, dict), ERROR_INFO.format(
        method=method, url=url, status=status
    )
    assert data["redis_ping"] == "pong", ERROR_INFO.format(
        method=method, url=url, status=status
    )
    assert data["postgres_ping"] == "pong", ERROR_INFO.format(
        method=method, url=url, status=status
    )
