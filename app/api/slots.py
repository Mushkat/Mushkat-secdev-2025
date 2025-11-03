from fastapi import APIRouter, Depends

from ..auth.dependencies import get_current_user
from ..schemas.validation import ParkingSlotCreate

router = APIRouter()

slots_db = []
next_slot_id = 1


@router.get("/slots")
async def get_slots(current_user: dict = Depends(get_current_user)):
    return slots_db


@router.post("/slots")
async def create_slot(slot_data: ParkingSlotCreate):
    global next_slot_id

    if any(slot["code"] == slot_data.code for slot in slots_db):
        from ..core.exceptions import ProblemDetailsException

        raise ProblemDetailsException(
            status_code=409,
            detail="Парковочное место с таким кодом уже существует",
            title="Conflict",
        )

    slot = {
        "id": next_slot_id,
        "code": slot_data.code,
        "description": slot_data.description,
    }
    slots_db.append(slot)
    next_slot_id += 1

    return slot
