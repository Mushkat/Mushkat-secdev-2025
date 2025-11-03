from fastapi import APIRouter

from ..auth.jwt_handler import create_access_token, get_password_hash
from ..core.exceptions import ProblemDetailsException
from ..schemas.validation import UserCreate

router = APIRouter()

users_db = {}


@router.post("/auth/register")
async def register(user_data: UserCreate):
    if user_data.email in users_db:
        raise ProblemDetailsException(
            status_code=409,
            detail="Пользователь с таким email уже существует",
            title="Conflict",
        )

    hashed_password = get_password_hash(user_data.password)
    users_db[user_data.email] = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
    }

    return {"message": "Пользователь успешно зарегистрирован"}


@router.post("/auth/login")
async def login(credentials: UserCreate):
    user = users_db.get(credentials.email)
    if not user:
        raise ProblemDetailsException(
            status_code=401, detail="Неверный email или пароль", title="Unauthorized"
        )

    from ..auth.jwt_handler import verify_password

    if not verify_password(credentials.password, user["hashed_password"]):
        raise ProblemDetailsException(
            status_code=401, detail="Неверный email или пароль", title="Unauthorized"
        )

    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}
