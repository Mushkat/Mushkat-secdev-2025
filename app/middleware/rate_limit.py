import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.exceptions import ProblemDetailsException


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limits: dict = None):
        super().__init__(app)
        self.requests = defaultdict(list)

        self.default_limits = {
            "global": {"max_requests": 1000, "window": 3600},
            "auth": {"max_requests": 10, "window": 60},
            "bookings": {"max_requests": 10, "window": 60},
            "availability": {"max_requests": 30, "window": 60},
        }

        if limits:
            self.default_limits.update(limits)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        path = request.url.path

        endpoint_type = self._get_endpoint_type(path)
        limits = self.default_limits.get(endpoint_type, self.default_limits["global"])

        max_requests = limits["max_requests"]
        window = limits["window"]

        key = f"{endpoint_type}:{client_ip}"

        self.requests[key] = [
            req_time
            for req_time in self.requests[key]
            if current_time - req_time < window
        ]

        if len(self.requests[key]) >= max_requests:
            retry_after = int(window - (current_time - self.requests[key][0]))

            raise ProblemDetailsException(
                status_code=429,
                detail=f"Слишком много запросов. Лимит: {max_requests} в {window} секунд",
                title="Too Many Requests",
                headers={"Retry-After": str(retry_after)},
            )

        self.requests[key].append(current_time)

        response = await call_next(request)
        return response

    def _get_endpoint_type(self, path: str) -> str:
        """Определяет тип эндпоинта для применения соответствующих лимитов"""
        if "/auth/login" in path or "/auth/register" in path:
            return "auth"
        elif "/bookings" in path and "POST" in path:
            return "bookings"
        elif "/availability" in path:
            return "availability"
        else:
            return "global"
