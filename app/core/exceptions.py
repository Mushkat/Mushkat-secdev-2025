"""Кастомный обработчик ошибок, возврат в RFC7807 формате."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Mapping, MutableMapping

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROBLEM_BASE_URI = "https://parking-slots.local/problems"


def _normalize_errors(errors: Mapping[str, Any] | None) -> Dict[str, list[str]]:
    if not errors:
        return {}
    normalized: Dict[str, list[str]] = {}
    for field, raw in errors.items():
        if isinstance(raw, (list, tuple, set)):
            normalized[field] = [str(item) for item in raw]
        else:
            normalized[field] = [str(raw)]
    return normalized


class APIError(HTTPException):
    """Исключение, генерирующее ответы RFC7807 с идентификаторами корреляции."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        title: str,
        detail: str | None = None,
        errors: Mapping[str, Any] | None = None,
        headers: MutableMapping[str, str] | None = None,
    ) -> None:
        self.code = code
        self.title = title
        self.detail = detail or title
        self.errors = _normalize_errors(errors)
        self.headers = dict(headers or {})
        super().__init__(status_code=status_code, detail=self.detail, headers=self.headers)


def _build_problem(
    request: Request,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str | None = None,
    errors: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    correlation_id = getattr(request.state, "correlation_id", None) or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    problem: Dict[str, Any] = {
        "type": f"{PROBLEM_BASE_URI}/{code.lower()}",
        "title": title,
        "status": status_code,
        "detail": detail or title,
        "instance": str(request.url.path),
        "code": code,
        "correlation_id": correlation_id,
    }
    normalized = _normalize_errors(errors)
    if normalized:
        problem["errors"] = normalized
    return problem


async def api_error_handler(request: Request, exc: APIError):
    body = _build_problem(
        request,
        status_code=exc.status_code,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        errors=exc.errors,
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def http_exception_handler(request: Request, exc: HTTPException):
    title = "HTTP error"
    body = _build_problem(
        request,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        title=title,
        detail=str(exc.detail) if exc.detail else title,
    )
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors: Dict[str, list[str]] = {}
    for err in exc.errors():
        location = ".".join(str(part) for part in err.get("loc", ())) or "unknown"
        errors.setdefault(location, []).append(err.get("msg", "invalid value"))

    body = _build_problem(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        title="Ошибка валидации входных данных",
        detail="Отправленные данные не прошли проверку",
        errors=errors,
    )
    return JSONResponse(status_code=422, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception):
    body = _build_problem(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        title="Внутренняя ошибка сервера",
        detail="Произошла непредвиденная ошибка",
    )
    return JSONResponse(status_code=500, content=body)
