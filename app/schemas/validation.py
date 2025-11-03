import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, constr, field_validator


class ParkingSlotCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=10)
    description: Optional[str] = None

    @field_validator("code")
    def code_uppercase(cls, v):
        if not re.match(r"^[A-Z0-9]{2,10}$", v):
            raise ValueError(
                "Code must contain only uppercase letters and numbers, 2-10 characters long"
            )
        return v.upper()


class BookingCreate(BaseModel):
    slot_id: int
    user_id: int
    date: date

    @field_validator("date")
    def date_not_in_past(cls, v):
        if v < date.today():
            raise ValueError("Дата бронирования не может быть в прошлом")
        return v


class UserCreate(BaseModel):
    email: EmailStr
    full_name: constr(min_length=1, max_length=100)
    password: constr(min_length=8, max_length=100)
