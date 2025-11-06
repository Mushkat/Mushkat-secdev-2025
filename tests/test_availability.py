from datetime import date, timedelta
from http import HTTPStatus


def test_availability_reflects_bookings(client, user_factory):
    owner_headers = user_factory("owner6@example.com")
    slot_response = client.post(
        "/api/v1/items",
        json={"code": "Z9", "description": "Roof"},
        headers=owner_headers,
    )
    slot = slot_response.json()

    booking_user = user_factory("viewer@example.com")
    target_date = date.today() + timedelta(days=3)

    client.post(
        "/api/v1/bookings",
        json={"slot_id": slot["id"], "booking_date": target_date.isoformat()},
        headers=booking_user,
    )

    availability = client.get(
        "/api/v1/availability",
        params={"target_date": target_date.isoformat()},
        headers=booking_user,
    )
    assert availability.status_code == HTTPStatus.OK
    body = availability.json()
    assert body["date"] == target_date.isoformat()
    assert len(body["slots"]) == 1
    assert body["slots"][0]["code"] == "Z9"
    assert body["slots"][0]["is_available"] is False

    invalid_code = client.get(
        "/api/v1/availability",
        params={"target_date": target_date.isoformat(), "code": "**"},
        headers=booking_user,
    )
    assert invalid_code.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    payload = invalid_code.json()
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["status"] == HTTPStatus.UNPROCESSABLE_ENTITY
    assert payload["errors"]["query.code"][0] == "некорректный формат"
