import time
from collections.abc import Callable
from typing import Any

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

HTTP_5XX_START = 500
HTTP_5XX_END = 600


REQUEST_COUNT = Counter(
    "fastapi_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Histogram автоматически создаёт _sum и _count
REQUEST_LATENCY = Histogram(
    "fastapi_requests_duration_seconds",
    "Request duration in seconds",
    ["endpoint", "method"],
)

REQUEST_IN_PROGRESS = Gauge(
    "fastapi_requests_inprogress", "Current number of in-progress requests"
)

RESPONSE_SIZE = Histogram(
    "fastapi_response_size_bytes",
    "Size of responses in bytes",
    ["endpoint", "method", "status"],
)

ERROR_COUNT = Counter(
    "fastapi_requests_errors_total",
    "Total number of failed requests (5xx)",
    ["method", "endpoint", "status"],
)


# ---------------- Middleware ----------------
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Any:  # type: ignore[type-arg]
        REQUEST_IN_PROGRESS.inc()  # Увеличиваем in-progress
        start_time = time.time()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            resp_time = time.time() - start_time
            REQUEST_IN_PROGRESS.dec()  # Уменьшаем in-progress

            # Количество запросов
            REQUEST_COUNT.labels(
                method=request.method, endpoint=request.url.path, status=status
            ).inc()

            # Длительность запроса (histogram создаёт _sum и _count)
            REQUEST_LATENCY.labels(
                endpoint=request.url.path, method=request.method
            ).observe(resp_time)

            # Размер ответа (если есть body)
            if "response" in locals() and hasattr(response, "body"):
                size = len(response.body) if response.body else 0
                RESPONSE_SIZE.labels(
                    endpoint=request.url.path,
                    method=request.method,
                    status=status,
                ).observe(size)

            # Ошибки 5xx
            if HTTP_5XX_START <= status < HTTP_5XX_END:
                ERROR_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=status,
                ).inc()
        return response
