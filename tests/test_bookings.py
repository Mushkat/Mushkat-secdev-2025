from datetime import date, timedelta
from http import HTTPStatus


def _create_item(client, headers, code="S1"):
    response = client.post(
        "/api/v1/items",
        json={"code": code, "description": "Test slot"},
        headers=headers,
    )
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


def test_create_booking_and_conflict_detection(client, user_factory):
    owner_headers = user_factory("owner3@example.com")
    item = _create_item(client, owner_headers, code="S10")

    user_headers = user_factory("driver@example.com")
    booking_date = date.today() + timedelta(days=1)

    first = client.post(
        "/api/v1/bookings",
        json={"slot_id": item["id"], "booking_date": booking_date.isoformat()},
        headers=user_headers,
    )
    assert first.status_code == HTTPStatus.CREATED

    conflict = client.post(
        "/api/v1/bookings",
        json={"slot_id": item["id"], "booking_date": booking_date.isoformat()},
        headers=user_headers,
    )
    assert conflict.status_code == HTTPStatus.CONFLICT
    conflict_body = conflict.json()
    assert conflict_body["code"] == "BOOKING_CONFLICT"
    assert conflict_body["errors"]["slot_id"][0] == "занят"
    assert conflict_body["errors"]["booking_date"][0] == "дата недоступна"
    assert conflict_body["type"].endswith("/booking_conflict")


def test_booking_status_transitions(client, user_factory):
    owner_headers = user_factory("owner4@example.com")
    item = _create_item(client, owner_headers, code="S11")
    user_headers = user_factory("driver2@example.com")
    booking_date = date.today() + timedelta(days=2)

    booking = client.post(
        "/api/v1/bookings",
        json={"slot_id": item["id"], "booking_date": booking_date.isoformat()},
        headers=user_headers,
    ).json()

    unauthorized_confirm = client.put(
        f"/api/v1/bookings/{booking['id']}",
        json={"status": "confirmed"},
        headers=user_headers,
    )
    assert unauthorized_confirm.status_code == HTTPStatus.FORBIDDEN
    unauthorized_body = unauthorized_confirm.json()
    assert unauthorized_body["code"] == "FORBIDDEN"
    assert unauthorized_body["title"] == "Недостаточно прав"

    confirmed = client.put(
        f"/api/v1/bookings/{booking['id']}",
        json={"status": "confirmed"},
        headers=owner_headers,
    )
    assert confirmed.status_code == HTTPStatus.OK
    assert confirmed.json()["status"] == "confirmed"

    cancelled = client.delete(
        f"/api/v1/bookings/{booking['id']}",
        headers=user_headers,
    )
    assert cancelled.status_code == HTTPStatus.NO_CONTENT

    rebook = client.post(
        "/api/v1/bookings",
        json={"slot_id": item["id"], "booking_date": booking_date.isoformat()},
        headers=user_headers,
    )
    assert rebook.status_code == HTTPStatus.CREATED


def test_booking_validation_rejects_past_date(client, user_factory):
    owner_headers = user_factory("owner5@example.com")
    item = _create_item(client, owner_headers, code="S12")
    user_headers = user_factory("driver3@example.com")
    past_date = date.today() - timedelta(days=1)

    response = client.post(
        "/api/v1/bookings",
        json={"slot_id": item["id"], "booking_date": past_date.isoformat()},
        headers=user_headers,
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    payload = response.json()
    assert payload["code"] == "VALIDATION_ERROR"
    assert any(
        "Дата бронирования" in message
        for message in payload["errors"]["body.booking_date"]
    )
