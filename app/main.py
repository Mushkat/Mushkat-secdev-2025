from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .api import auth, slots
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware

app = FastAPI(title="Parking slots App", version="0.1.0")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(slots.router, prefix="/api/v1", tags=["slots"])


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Normalize FastAPI HTTPException into our error envelope
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


_DB = {"items": []}


@app.post("/items")
def create_item(name: str):
    if not name or len(name) > 100:
        raise ApiError(
            code="validation_error", message="name must be 1..100 chars", status=422
        )
    item = {"id": len(_DB["items"]) + 1, "name": name}
    _DB["items"].append(item)
    return item


@app.get("/items/{item_id}")
def get_item(item_id: int):
    for it in _DB["items"]:
        if it["id"] == item_id:
            return it
    raise ApiError(code="not_found", message="item not found", status=404)


app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(slots.router, prefix="/api/v1", tags=["slots"])


@app.get("/")
async def root():
    return {"message": "Parking slots API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "parking-slots-api"}
