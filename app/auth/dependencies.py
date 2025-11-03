from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_handler import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Зависимость для получения текущего пользователя из JWT токена
    """
    token = credentials.credentials

    try:
        payload = verify_token(token)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
