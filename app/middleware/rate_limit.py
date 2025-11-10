import os
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.exceptions import APIError


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limits: dict = None, disable: bool | None = None):
        super().__init__(app)
        self.requests = defaultdict(list)
        if disable is None:
            self.disabled = os.getenv("DISABLE_RATE_LIMIT", "0") == "1"
        else:
            self.disabled = disable

        self.default_limits = {
            "global": {"max_requests": 1000, "window": 3600},
            "auth": {"max_requests": 10, "window": 60},
            "bookings": {"max_requests": 10, "window": 60},
            "availability": {"max_requests": 30, "window": 60},
        }

        if limits:
            self.default_limits.update(limits)

    async def dispatch(self, request: Request, call_next):
        if self.disabled:
            return await call_next(request)

        client_ip = request.client.host
        current_time = time.time()
        endpoint_type = self._get_endpoint_type(request)
        limits = self.default_limits.get(endpoint_type, self.default_limits["global"])

        max_requests = limits["max_requests"]
        window = limits["window"]

        key = f"{endpoint_type}:{client_ip}"

        self.requests[key] = [
            req_time for req_time in self.requests[key] if current_time - req_time < window
        ]

        if len(self.requests[key]) >= max_requests:
            retry_after = int(window - (current_time - self.requests[key][0]))

            raise APIError(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                title="Превышен лимит запросов",
                detail=f"Слишком много запросов. Лимит: {max_requests} в {window} секунд",
                errors={"retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )

        self.requests[key].append(current_time)

        response = await call_next(request)
        return response

    def _get_endpoint_type(self, request: Request) -> str:
        """Определяет тип эндпоинта для применения соответствующих лимитов"""
        path = request.url.path
        method = request.method.upper()
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
            return "auth"
        elif path.startswith("/api/v1/bookings") and method == "POST":
            return "bookings"
        elif path.startswith("/api/v1/availability"):
            return "availability"
        else:
            return "global"
