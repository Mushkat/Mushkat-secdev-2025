from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_error_format_validation():
    """Тест формата ошибки валидации через middleware"""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid-email", "full_name": "Test User", "password": "short"},
    )

    assert response.status_code == 422
    data = response.json()

    assert "detail" in data
    assert isinstance(data["detail"], list)

    assert len(data["detail"]) > 0
    error_fields = [error["loc"] for error in data["detail"]]
    assert any("email" in str(loc) for loc in error_fields)
    assert any("password" in str(loc) for loc in error_fields)


def test_auth_middleware_protection():
    """Тест защиты эндпоинтов middleware аутентификации"""
    response = client.get("/api/v1/slots")
    assert response.status_code == 403
