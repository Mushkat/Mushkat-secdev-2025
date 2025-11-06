from sqlite3 import Connection

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_handler import verify_token
from app.core.database import get_db
from app.core.exceptions import APIError

security = HTTPBearer(auto_error=False)


def _auth_error(title: str, detail: str) -> APIError:
    return APIError(
        status_code=401,
        code="AUTHENTICATION_FAILED",
        title=title,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn: Connection = Depends(get_db),
):
    if credentials is None:
        raise _auth_error(
            "Требуется аутентификация", "Для доступа необходим Bearer токен"
        )

    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise _auth_error(
            "Некорректный токен аутентификации",
            "В токене отсутствуют обязательные поля",
        )

    conn.execute("DELETE FROM revoked_tokens WHERE expires_at <= CURRENT_TIMESTAMP")
    revoked = conn.execute(
        "SELECT 1 FROM revoked_tokens WHERE jti = ?",
        (jti,),
    ).fetchone()
    if revoked:
        raise _auth_error("Токен отозван", "Необходимо выполнить повторный вход")

    row = conn.execute(
        "SELECT id, email, full_name, role FROM users WHERE id = ?",
        (int(user_id),),
    ).fetchone()
    if row is None:
        raise _auth_error(
            "Пользователь не найден", "Учетная запись была удалена или не существует"
        )

    user = dict(row)
    request.state.user = {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
    }
    request.state.token_jti = jti
    request.state.raw_token = token
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Доступ доступен только администраторам",
        )
    return current_user
