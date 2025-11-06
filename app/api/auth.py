from datetime import datetime, timezone
from sqlite3 import Connection

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from ..auth.dependencies import security
from ..auth.jwt_handler import create_access_token, get_password_hash, verify_password, verify_token
from ..core.database import get_db
from ..core.exceptions import APIError
from ..schemas.validation import TokenResponse, UserCreate, UserLogin, UserRead

router = APIRouter()


@router.post(
    "/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate, conn: Connection = Depends(get_db)):
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", (user_data.email,)
    ).fetchone()
    if existing:
        raise APIError(
            status_code=409,
            code="USER_ALREADY_EXISTS",
            title="Пользователь уже существует",
            detail="Пользователь с таким email уже существует",
            errors={"email": "уже зарегистрирован"},
        )

    hashed_password = get_password_hash(user_data.password)
    cursor = conn.execute(
        "INSERT INTO users (email, full_name, hashed_password, role) VALUES (?, ?, ?, 'user')",
        (user_data.email, user_data.full_name, hashed_password),
    )
    user_id = cursor.lastrowid
    conn.commit()
    row = conn.execute(
        "SELECT id, email, full_name, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return dict(row)


@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, conn: Connection = Depends(get_db)):
    row = conn.execute(
        "SELECT id, email, hashed_password FROM users WHERE email = ?",
        (credentials.email,),
    ).fetchone()
    if not row or not verify_password(credentials.password, row["hashed_password"]):
        raise APIError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            title="Неверный email или пароль",
            detail="Проверьте правильность учетных данных",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(row["id"])})
    return TokenResponse(access_token=access_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn: Connection = Depends(get_db),
):
    if credentials is None:
        raise APIError(
            status_code=401,
            code="AUTHENTICATION_FAILED",
            title="Требуется токен для выхода",
            detail="Для выполнения действия необходим Bearer токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        raise APIError(
            status_code=401,
            code="INVALID_TOKEN",
            title="Некорректный токен",
            detail="Токен не содержит обязательных полей",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    conn.execute(
        "INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
        (jti, expires_at),
    )
    conn.commit()
    return None
