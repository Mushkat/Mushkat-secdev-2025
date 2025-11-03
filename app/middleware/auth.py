from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth.jwt_handler import verify_token
from ..core.exceptions import ProblemDetailsException


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        ]

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise ProblemDetailsException(
                status_code=401, detail="Требуется аутентификация", title="Unauthorized"
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise ProblemDetailsException(
                status_code=401,
                detail="Неверный формат заголовка Authorization. Ожидается: Bearer <token>",
                title="Unauthorized",
            )

        token = parts[1]

        try:
            payload = verify_token(token)
            request.state.user = payload
        except HTTPException:
            raise ProblemDetailsException(
                status_code=401,
                detail="Невалидный или просроченный токен",
                title="Unauthorized",
            )

        return await call_next(request)
