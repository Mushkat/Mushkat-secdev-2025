import uuid
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class ProblemDetailsException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        title: str = None,
        type: str = None,
        instance: str = None,
        headers: Dict[str, Any] = None,
    ):
        if title is None:
            title = {
                400: "Bad Request",
                401: "Unauthorized",
                403: "Forbidden",
                404: "Not Found",
                409: "Conflict",
                429: "Too Many Requests",
                500: "Internal Server Error",
            }.get(status_code, "Error")

        if type is None:
            type = f"https://httpstatuses.com/{status_code}"

        self.problem_details = {
            "type": type,
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
            "correlation_id": str(uuid.uuid4()),
        }
        super().__init__(status_code=status_code, detail=detail, headers=headers)


async def problem_details_exception_handler(request, exc: ProblemDetailsException):
    return JSONResponse(
        status_code=exc.status_code, content=exc.problem_details, headers=exc.headers
    )
