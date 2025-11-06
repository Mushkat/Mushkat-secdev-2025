from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query, status

from ..auth.dependencies import get_current_user
from ..core.database import get_db
from ..core.exceptions import APIError
from ..schemas.validation import ItemCreate, ItemRead, ItemsPage, ItemUpdate

router = APIRouter()


@router.get("/items", response_model=ItemsPage)
async def list_items(
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    base_params: list[int] = []
    where_clause = ""
    if current_user["role"] != "admin":
        where_clause = " WHERE owner_id = ?"
        base_params.append(current_user["id"])

    total = conn.execute(
        f"SELECT COUNT(1) FROM slots{where_clause}",
        tuple(base_params),
    ).fetchone()[0]

    rows = conn.execute(
        f"SELECT id, code, description, owner_id FROM slots{where_clause}"
        " ORDER BY code LIMIT ? OFFSET ?",
        tuple(base_params + [limit, offset]),
    ).fetchall()

    items = [dict(row) for row in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    existing = conn.execute(
        "SELECT id FROM slots WHERE code = ?", (item_data.code,)
    ).fetchone()
    if existing:
        raise APIError(
            status_code=409,
            code="ITEM_ALREADY_EXISTS",
            title="Предмет уже существует",
            detail="Предмет с таким кодом уже существует",
            errors={"code": "уже занят"},
        )

    cursor = conn.execute(
        "INSERT INTO slots (code, description, owner_id) VALUES (?, ?, ?)",
        (item_data.code, item_data.description, current_user["id"]),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, code, description, owner_id FROM slots WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return dict(row)


@router.get("/items/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT id, code, description, owner_id FROM slots WHERE id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise APIError(
            status_code=404,
            code="ITEM_NOT_FOUND",
            title="Предмет не найден",
            detail="Запрошенный предмет отсутствует или удален",
            errors={"item_id": "не существует"},
        )
    if row["owner_id"] != current_user["id"] and current_user["role"] != "admin":
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Недостаточно прав для доступа к предмету",
        )
    return dict(row)


@router.patch("/items/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT id, owner_id FROM slots WHERE id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise APIError(
            status_code=404,
            code="ITEM_NOT_FOUND",
            title="Предмет не найден",
            detail="Запрошенный предмет отсутствует или удален",
            errors={"item_id": "не существует"},
        )
    if row["owner_id"] != current_user["id"] and current_user["role"] != "admin":
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Недостаточно прав для изменения предмета",
        )

    if item_update.description is not None:
        conn.execute(
            "UPDATE slots SET description = ? WHERE id = ?",
            (item_update.description, item_id),
        )
        conn.commit()

    updated = conn.execute(
        "SELECT id, code, description, owner_id FROM slots WHERE id = ?",
        (item_id,),
    ).fetchone()
    return dict(updated)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT owner_id FROM slots WHERE id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise APIError(
            status_code=404,
            code="ITEM_NOT_FOUND",
            title="Предмет не найден",
            detail="Запрошенный предмет отсутствует или удален",
            errors={"item_id": "не существует"},
        )
    if row["owner_id"] != current_user["id"] and current_user["role"] != "admin":
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            title="Недостаточно прав",
            detail="Недостаточно прав для удаления предмета",
        )

    conn.execute("DELETE FROM slots WHERE id = ?", (item_id,))
    conn.commit()
    return None
