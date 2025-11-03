import time
from collections import defaultdict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)

    async def check_rate_limit(
        self, request: Request, max_requests: int = 10, window: int = 60
    ):
        client_ip = request.client.host
        current_time = time.time()

        self.requests[client_ip] = [
            req_time
            for req_time in self.requests[client_ip]
            if current_time - req_time < window
        ]

        if len(self.requests[client_ip]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Слишком много запросов. Лимит: {max_requests} в {window} секунд",
            )

        self.requests[client_ip].append(current_time)


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    try:
        await rate_limiter.check_rate_limit(request)
        response = await call_next(request)
        return response
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
