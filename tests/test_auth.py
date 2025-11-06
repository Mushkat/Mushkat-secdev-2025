from http import HTTPStatus


def test_register_and_login_success(client):
    payload = {
        "email": "alice@example.com",
        "full_name": "Alice Example",
        "password": "SecurePass1",
    }
    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == HTTPStatus.CREATED
    body = register_response.json()
    assert body["email"] == payload["email"]
    assert body["role"] == "user"
    assert "id" in body

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == HTTPStatus.OK
    token_body = login_response.json()
    assert "access_token" in token_body
    assert token_body["token_type"] == "bearer"


def test_register_duplicate_email(client):
    payload = {
        "email": "bob@example.com",
        "full_name": "Bob Example",
        "password": "AnotherPass1",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == HTTPStatus.CREATED

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == HTTPStatus.CONFLICT
    detail = second.json()
    assert detail["code"] == "USER_ALREADY_EXISTS"
    assert detail["status"] == HTTPStatus.CONFLICT
    assert detail["title"] == "Пользователь уже существует"
    assert detail["detail"] == "Пользователь с таким email уже существует"
    assert detail["type"].endswith("/user_already_exists")
    assert detail["errors"]["email"][0] == "уже зарегистрирован"
    assert "correlation_id" in detail


def test_login_invalid_password(client):
    payload = {
        "email": "charlie@example.com",
        "full_name": "Charlie Example",
        "password": "ValidPass1",
    }
    client.post("/api/v1/auth/register", json=payload)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPass1"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    body = response.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["status"] == HTTPStatus.UNAUTHORIZED
    assert body["title"] == "Неверный email или пароль"
    assert body["detail"] == "Проверьте правильность учетных данных"
    assert body["type"].endswith("/invalid_credentials")
    assert "correlation_id" in body


def test_logout_revokes_token(client, user_factory):
    headers = user_factory("logout@example.com")

    protected = client.get("/api/v1/items", headers=headers)
    assert protected.status_code == HTTPStatus.OK

    logout_response = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == HTTPStatus.NO_CONTENT

    after_logout = client.get("/api/v1/items", headers=headers)
    assert after_logout.status_code == HTTPStatus.UNAUTHORIZED
    body = after_logout.json()
    assert body["code"] == "AUTHENTICATION_FAILED"
    assert body["type"].endswith("/authentication_failed")
