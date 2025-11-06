from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from app.api import auth, availability, bookings, items
from app.auth.bootstrap import ensure_default_admin
from app.core.database import init_db
from app.core.exceptions import (
    APIError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.middleware.rate_limit import RateLimitMiddleware

exception_handlers = {
    APIError: api_error_handler,
    HTTPException: http_exception_handler,
    RequestValidationError: validation_exception_handler,
    Exception: unhandled_exception_handler,
}

app = FastAPI(
    title="Parking slots App", version="0.1.0", exception_handlers=exception_handlers
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    ensure_default_admin()


app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(bookings.router, prefix="/api/v1", tags=["bookings"])
app.include_router(availability.router, prefix="/api/v1", tags=["availability"])


@app.get("/")
async def root():
    return {"message": "Parking slots API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "parking-slots-api"}
