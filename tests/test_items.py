from http import HTTPStatus


def test_create_item_and_paginate(client, user_factory):
    headers = user_factory("owner@example.com")

    created_ids: list[int] = []
    for idx in range(3):
        response = client.post(
            "/api/v1/items",
            json={"code": f"S{idx}", "description": f"Spot {idx}"},
            headers=headers,
        )
        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        created_ids.append(body["id"])
        assert body["owner_id"] > 0

    list_response = client.get("/api/v1/items", headers=headers, params={"limit": 2, "offset": 0})
    assert list_response.status_code == HTTPStatus.OK
    payload = list_response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert [item["code"] for item in payload["items"]] == ["S0", "S1"]

    second_page = client.get("/api/v1/items", headers=headers, params={"limit": 2, "offset": 2})
    assert second_page.status_code == HTTPStatus.OK
    second_payload = second_page.json()
    assert second_payload["items"][0]["id"] == created_ids[2]
    assert second_payload["limit"] == 2
    assert second_payload["offset"] == 2


def test_item_conflict_returns_structured_error(client, user_factory):
    headers = user_factory("conflict@example.com")
    client.post(
        "/api/v1/items",
        json={"code": "D1", "description": "First"},
        headers=headers,
    )

    conflict = client.post(
        "/api/v1/items",
        json={"code": "D1", "description": "Duplicate"},
        headers=headers,
    )
    assert conflict.status_code == HTTPStatus.CONFLICT
    body = conflict.json()
    assert body["code"] == "ITEM_ALREADY_EXISTS"
    assert body["status"] == HTTPStatus.CONFLICT
    assert body["errors"]["code"][0] == "уже занят"
    assert body["type"].endswith("/item_already_exists")
    assert "correlation_id" in body


def test_item_access_restricted_to_owner_or_admin(client, user_factory):
    owner_headers = user_factory("owner2@example.com")
    other_headers = user_factory("intruder@example.com")
    admin_headers = user_factory("admin@example.com", role="admin")

    item = client.post(
        "/api/v1/items",
        json={"code": "ZZ", "description": "Original"},
        headers=owner_headers,
    ).json()

    forbidden = client.get(f"/api/v1/items/{item['id']}", headers=other_headers)
    assert forbidden.status_code == HTTPStatus.FORBIDDEN
    forbidden_body = forbidden.json()
    assert forbidden_body["code"] == "FORBIDDEN"
    assert forbidden_body["title"] == "Недостаточно прав"

    admin_view = client.get(f"/api/v1/items/{item['id']}", headers=admin_headers)
    assert admin_view.status_code == HTTPStatus.OK
    assert admin_view.json()["code"] == "ZZ"

    update = client.patch(
        f"/api/v1/items/{item['id']}",
        json={"description": "Updated"},
        headers=admin_headers,
    )
    assert update.status_code == HTTPStatus.OK
    assert update.json()["description"] == "Updated"

    delete_response = client.delete(f"/api/v1/items/{item['id']}", headers=admin_headers)
    assert delete_response.status_code == HTTPStatus.NO_CONTENT
