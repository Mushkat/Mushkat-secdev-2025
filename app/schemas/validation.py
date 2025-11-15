import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt, field_validator

from app.core.models import BookingStatus

CODE_PATTERN = re.compile(r"^[A-Z0-9]{2,10}$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,64}$")


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError(
                "Пароль должен содержать строчные и прописные буквы, цифру "
                "и быть длиной 8-64 символа"
            )

        if len(value.encode("utf-8")) > 72:
            raise ValueError("Пароль после UTF-8 кодирования не может превышать 72 байта")

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ItemBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=10)
    description: Optional[str] = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, value: str) -> str:
        if not CODE_PATTERN.match(value):
            raise ValueError("Код должен состоять из 2-10 символов A-Z или 0-9")
        return value


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=255)


class ItemRead(ItemBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)


class ItemsPage(BaseModel):
    items: list[ItemRead]
    total: int
    limit: int
    offset: int


class BookingBase(BaseModel):
    slot_id: PositiveInt
    booking_date: date

    @field_validator("booking_date")
    @classmethod
    def not_in_past(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("Дата бронирования не может быть в прошлом")
        return value


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    status: BookingStatus


class BookingRead(BaseModel):
    id: int
    slot_id: int
    user_id: int
    booking_date: date
    status: BookingStatus

    model_config = ConfigDict(from_attributes=True)


class AvailabilityItem(BaseModel):
    slot_id: int
    code: str
    is_available: bool


class AvailabilityResponse(BaseModel):
    date: date
    slots: list[AvailabilityItem]
