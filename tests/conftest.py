import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from urllib.parse import urlencode

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DATABASE_URL = "sqlite:///./test_app.db"
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("DISABLE_RATE_LIMIT", "1")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-0123456789abcdef0123456789",
)

from app.core import database as db  # noqa: E402
from app.core.database import get_db, init_db  # noqa: E402
from app.main import app  # noqa: E402


class _SimpleResponse:
    def __init__(self, status_code: int, body: bytes, headers: Iterable[Tuple[bytes, bytes]]):
        self.status_code = status_code
        self._body = body
        self.headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in headers}

    def json(self) -> Any:
        if not self._body:
            return None
        return json.loads(self._body.decode("utf-8"))

    def text(self) -> str:
        return self._body.decode("utf-8")


class SimpleASGITestClient:
    def __init__(self, asgi_app):
        self.app = asgi_app
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.app.router.startup())

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Dict[str, str] | None = None,
        params: Dict[str, Any] | None = None,
        json_data: Any = None,
        data: bytes | None = None,
    ) -> _SimpleResponse:
        path = url
        query_string = b""
        if params:
            query = urlencode(params, doseq=True)
            path = f"{path}?{query}" if "?" not in path else f"{path}&{query}"
            query_string = query.encode("utf-8")

        body = b""
        send_headers = {key.lower(): value for key, value in (headers or {}).items()}
        if json_data is not None:
            body = json.dumps(json_data, ensure_ascii=False).encode("utf-8")
            send_headers.setdefault("content-type", "application/json")
        elif data is not None:
            body = data

        raw_headers = [
            (key.encode("latin-1"), value.encode("latin-1")) for key, value in send_headers.items()
        ]
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "path": path.split("?")[0],
            "raw_path": path.encode("latin-1"),
            "query_string": query_string,
            "headers": raw_headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
        }

        body_sent = False
        response_data: Dict[str, Any] = {"body": b"", "headers": []}

        async def receive() -> Dict[str, Any]:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: Dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_data["status"] = message["status"]
                response_data["headers"] = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response_data["body"] += message.get("body", b"")

        await self.app(scope, receive, send)

        status_code = response_data.get("status", 500)
        return _SimpleResponse(status_code, response_data["body"], response_data["headers"])

    def request(self, method: str, url: str, **kwargs: Any) -> _SimpleResponse:
        json_data = kwargs.pop("json", None)
        return self.loop.run_until_complete(
            self._request(method, url, json_data=json_data, **kwargs)
        )

    def get(self, url: str, **kwargs: Any) -> _SimpleResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> _SimpleResponse:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> _SimpleResponse:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> _SimpleResponse:
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> _SimpleResponse:
        return self.request("PATCH", url, **kwargs)

    def close(self) -> None:
        self.loop.run_until_complete(self.app.router.shutdown())
        asyncio.set_event_loop(None)
        self.loop.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def reset_database() -> None:
    init_db()
    with db.connect() as conn:
        conn.execute("DELETE FROM bookings")
        conn.execute("DELETE FROM slots")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM revoked_tokens")
        conn.commit()


app.dependency_overrides[get_db] = get_db


@pytest.fixture(autouse=True)
def _prepare_db():
    reset_database()
    yield
    reset_database()


@pytest.fixture()
def client():
    with SimpleASGITestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user_factory(client):
    created_users: set[str] = set()

    def _create_user(
        email: str,
        password: str = "Password1!",
        full_name: str = "Test User",
        role: str = "user",
    ):
        if email not in created_users:
            response = client.post(
                "/api/v1/auth/register",
                json={"email": email, "full_name": full_name, "password": password},
            )
            assert response.status_code in {201, 409}
            created_users.add(email)
            if role == "admin":
                with db.connect() as conn:
                    conn.execute(
                        "UPDATE users SET role = 'admin' WHERE email = ?",
                        (email,),
                    )
                    conn.commit()
        login_response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _create_user
