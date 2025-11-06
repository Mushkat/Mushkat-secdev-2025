from sqlite3 import Connection

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import APIError
from app.core.models import BookingStatus
from app.schemas.validation import BookingCreate, BookingRead, BookingUpdate

router = APIRouter()


@router.get("/bookings", response_model=list[BookingRead])
async def list_bookings(
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
    slot_id: int | None = None,
):
    if current_user["role"] == "admin":
        query = [
            "SELECT b.id, b.slot_id, b.user_id, b.booking_date, b.status",
            "FROM bookings b",
        ]
        params: list[int] = []
        if slot_id is not None:
            query.append("WHERE b.slot_id = ?")
            params.append(slot_id)
    else:
        query = [
            "SELECT b.id, b.slot_id, b.user_id, b.booking_date, b.status",
            "FROM bookings b",
            "JOIN slots s ON s.id = b.slot_id",
            "WHERE (b.user_id = ? OR s.owner_id = ?)",
        ]
        params = [current_user["id"], current_user["id"]]
        if slot_id is not None:
            query.append("AND b.slot_id = ?")
            params.append(slot_id)
    query.append("ORDER BY b.booking_date ASC, b.id ASC")
    rows = conn.execute("\n".join(query), tuple(params)).fetchall()
    return [dict(row) for row in rows]


@router.post(
    "/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED
)
async def create_booking(
    booking_data: BookingCreate,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    slot = conn.execute(
        "SELECT id FROM slots WHERE id = ?",
        (booking_data.slot_id,),
    ).fetchone()
    if slot is None:
        raise APIError(
            status_code=404,
            code="ITEM_NOT_FOUND",
            title="Парковочное место не найдено",
            detail="Указанный слот отсутствует или был удален",
            errors={"slot_id": "не существует"},
        )

    conflict = conn.execute(
        """
        SELECT id FROM bookings
        WHERE slot_id = ? AND booking_date = ? AND status != ?
        LIMIT 1
        """,
        (
            booking_data.slot_id,
            booking_data.booking_date,
            BookingStatus.CANCELLED.value,
        ),
    ).fetchone()
    if conflict:
        raise APIError(
            status_code=409,
            code="BOOKING_CONFLICT",
            title="Слот уже занят",
            detail="Слот уже забронирован на выбранную дату",
            errors={
                "slot_id": "занят",
                "booking_date": "дата недоступна",
            },
        )

    cursor = conn.execute(
        """
        INSERT INTO bookings (slot_id, user_id, booking_date, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            booking_data.slot_id,
            current_user["id"],
            booking_data.booking_date,
            BookingStatus.PENDING.value,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, slot_id, user_id, booking_date, status FROM bookings WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return dict(row)


@router.get("/bookings/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    record = conn.execute(
        """
        SELECT b.id, b.slot_id, b.user_id, b.booking_date, b.status, s.owner_id
        FROM bookings b
        JOIN slots s ON s.id = b.slot_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()
    if record is None:
        raise APIError(
            status_code=404,
            code="BOOKING_NOT_FOUND",
            title="Бронирование не найдено",
            detail="Запрошенное бронирование отсутствует",
            errors={"booking_id": "не существует"},
        )
    if current_user["role"] != "admin" and current_user["id"] not in {
        record["user_id"],
        record["owner_id"],
    }:
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Недостаточно прав для просмотра бронирования",
        )
    return {
        key: record[key]
        for key in ("id", "slot_id", "user_id", "booking_date", "status")
    }


@router.put("/bookings/{booking_id}", response_model=BookingRead)
async def update_booking(
    booking_id: int,
    payload: BookingUpdate,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    record = conn.execute(
        """
        SELECT b.id, b.slot_id, b.user_id, b.booking_date, b.status, s.owner_id
        FROM bookings b
        JOIN slots s ON s.id = b.slot_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()
    if record is None:
        raise APIError(
            status_code=404,
            code="BOOKING_NOT_FOUND",
            title="Бронирование не найдено",
            detail="Запрошенное бронирование отсутствует",
            errors={"booking_id": "не существует"},
        )

    is_slot_owner = record["owner_id"] == current_user["id"]
    is_booking_owner = record["user_id"] == current_user["id"]
    is_admin = current_user["role"] == "admin"

    if payload.status == BookingStatus.CONFIRMED and not (is_slot_owner or is_admin):
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Только владелец слота или администратор может подтверждать",
        )

    if payload.status == BookingStatus.PENDING and not (is_slot_owner or is_admin):
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Только владелец слота или администратор может изменять статус",
        )

    if payload.status == BookingStatus.CANCELLED and not (
        is_slot_owner or is_booking_owner or is_admin
    ):
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Недостаточно прав для отмены",
        )

    if payload.status != BookingStatus.CANCELLED:
        conflict = conn.execute(
            """
            SELECT id FROM bookings
            WHERE id != ? AND slot_id = ? AND booking_date = ? AND status != ?
            LIMIT 1
            """,
            (
                booking_id,
                record["slot_id"],
                record["booking_date"],
                BookingStatus.CANCELLED.value,
            ),
        ).fetchone()
        if conflict:
            raise APIError(
                status_code=409,
                code="BOOKING_CONFLICT",
                title="Слот уже занят",
                detail="Слот уже забронирован на выбранную дату",
                errors={"booking_id": "конфликт"},
            )

    conn.execute(
        """
        UPDATE bookings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """,
        (payload.status.value, booking_id),
    )
    conn.commit()
    updated = conn.execute(
        "SELECT id, slot_id, user_id, booking_date, status FROM bookings WHERE id = ?",
        (booking_id,),
    ).fetchone()
    return dict(updated)


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    record = conn.execute(
        """
        SELECT b.user_id, s.owner_id
        FROM bookings b
        JOIN slots s ON s.id = b.slot_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()
    if record is None:
        raise APIError(
            status_code=404,
            code="BOOKING_NOT_FOUND",
            title="Бронирование не найдено",
            detail="Запрошенное бронирование отсутствует",
            errors={"booking_id": "не существует"},
        )
    if current_user["role"] != "admin" and current_user["id"] not in {
        record["user_id"],
        record["owner_id"],
    }:
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Недостаточно прав для отмены",
        )

    conn.execute(
        "UPDATE bookings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (BookingStatus.CANCELLED.value, booking_id),
    )
    conn.commit()
    return None
