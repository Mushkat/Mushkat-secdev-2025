from datetime import date
from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import APIError
from app.core.models import BookingStatus
from app.schemas.validation import CODE_PATTERN, AvailabilityItem, AvailabilityResponse

router = APIRouter()


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    target_date: date = Query(
        ..., description="Дата, для которой рассчитывается доступность"
    ),
    code: str | None = Query(None, description="Фильтр по коду парковочного места"),
    _: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    normalized_code = None
    if code:
        normalized_code = code.strip().upper()
        if not CODE_PATTERN.match(normalized_code):
            raise APIError(
                status_code=422,
                code="VALIDATION_ERROR",
                title="Неверный формат кода парковочного места",
                detail="Код может содержать только символы A-Z и цифры",
                errors={"query.code": "некорректный формат"},
            )

    if normalized_code:
        slots = conn.execute(
            "SELECT id, code FROM slots WHERE code = ? ORDER BY code",
            (normalized_code,),
        ).fetchall()
    else:
        slots = conn.execute("SELECT id, code FROM slots ORDER BY code").fetchall()

    booked_rows = conn.execute(
        """
        SELECT slot_id FROM bookings
        WHERE booking_date = ? AND status != ?
        """,
        (target_date, BookingStatus.CANCELLED.value),
    ).fetchall()
    booked_slot_ids = {row["slot_id"] for row in booked_rows}

    items = [
        AvailabilityItem(
            slot_id=row["id"],
            code=row["code"],
            is_available=row["id"] not in booked_slot_ids,
        )
        for row in slots
    ]

    return AvailabilityResponse(date=target_date, slots=items)
