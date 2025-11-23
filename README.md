# Parking Slots API

Минимально жизнеспособный сервис бронирования парковочных мест. Реализация соответствует требованиям курса P06 — Secure Coding: входные данные валидируются строгими схемами, ошибки возвращаются в формате RFC 7807 с `correlation_id`, все SQL-запросы параметризованы, а секреты и лимиты читаются из переменных окружения.
Для корректного запуска в .env задать случайное значение для переменной из .env.example - JWT_SECRET_KEY.
## Быстрый старт
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
uvicorn app.main:app --reload --env-file .env
```

## Ритуал перед PR
```bash
ruff check --fix .
black .
isort .
pytest -q
pre-commit run --all-files
```

## Тесты
```bash
pytest -q
```

## CI
В репозитории настроен workflow **CI** (GitHub Actions) — required check для `main`.
Badge добавится автоматически после загрузки шаблона в GitHub.

## Контейнеры
```bash
docker build -t secdev-app .
docker run --rm -p 8000:8000 secdev-app
# или
docker compose up --build
```

## Эндпойнты
- `GET /health` → `{"status": "ok"}`
- `POST /items?name=...` — демо-сущность
- `GET /items/{id}`

## Формат ошибок
Все ошибки — JSON-обёртка:
```json
{
  "error": {"code": "not_found", "message": "item not found"}
}
```
## Запуск приложения

1. Убедитесь, что установлен Python 3.11 или новее
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
3. Запустите приложение:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Приложение будет доступно по адресу: http://localhost:8000
5. Документация API: http://localhost:8000/docs

## Запуск тестов

```bash
pytest -q
```
> Для локальной разработки можно отключить rate-limit, установив `DISABLE_RATE_LIMIT=1`. JWT секрет должен быть не короче 32 символов.

## Контейнеризация и харднинг

### Что внутри Dockerfile
- multi-stage сборка на `python:3.12.3-slim` с отдельными стадиями `deps` (зависимости), `tester` (pytest) и `runtime`;
- runtime-образ содержит только prod-зависимости, файловую систему `/app` в режиме read-only и том `/data` для SQLite;
- пользователь `app` без root-прав, `cap_drop: ALL`, `no-new-privileges`, healthcheck через `scripts/healthcheck.py`.

### Сборка и запуск локально
```bash
docker compose build --pull --no-cache
docker compose up -d
docker compose ps
curl -f http://localhost:8000/health
```

Полезные проверки:
- убедиться, что процесс не под root: `docker compose exec api id -u` (должен вернуть `1000+`);
- убедиться, что healthcheck перешёл в `healthy`: `docker inspect --format '{{.State.Health.Status}}' $(docker compose ps -q api)`;
- посмотреть размер и слои образа:
  ```bash
  docker images parking-slots-api:local
  docker history parking-slots-api:local
  ```
- остановить сервис: `docker compose down -v`.

### CI-проверки
- Job `container-security` в `.github/workflows/ci.yml` последовательно запускает `hadolint`, `docker build`, проверку `id -u`, healthcheck контейнера и `trivy`;
- отчёты `trivy-report.sarif`, `docker-history.txt`, `docker-images.txt` публикуются артефактами GitHub Actions для вложения в PR (C1/C4);
- команды для локальной проверки линтера Dockerfile: `docker run --rm -i hadolint/hadolint < Dockerfile`;
- для сканирования образа локально можно использовать `trivy image parking-slots-api:local`.

### Compose-окружение (C3–C5)
- `docker-compose.yml` описывает сервис `api` и том `app-data` с ограничениями (read-only rootfs, tmpfs для `/tmp`);
- `.env` содержит все необходимые переменные (`JWT_SECRET_KEY`, `DATABASE_URL`, лимиты). Значение по умолчанию записывает БД в `/data` и монтирует его как volume;
- процесс CI поднимает контейнер, проверяет `/health` и выгружает логи, что демонстрирует готовность сервисов для локального запуска/ревью.

## Архитектура
- FastAPI + встроенный SQLite (`sqlite:///parking.db` по умолчанию, путь можно задать через `DATABASE_URL`).
- Аутентификация по JWT, пароли хэшируются через `bcrypt`.
- Доступ к данным реализован на стандартном модуле `sqlite3` c параметризацией запросов.
- Rate limit middleware по умолчанию защищает чувствительные маршруты (POST /bookings, /auth/*). Отключается через `DISABLE_RATE_LIMIT`.

## Таблицы
- **users**: `id`, `email` (уникальный), `full_name`, `hashed_password`, `role` (`user|admin`).
- **slots**: `id`, `code` (уникальный), `description`, `owner_id`.
- **bookings**: `id`, `slot_id`, `user_id`, `booking_date`, `status` (`pending|confirmed|cancelled`).
- **revoked_tokens**: `jti`, `expires_at` — отозванные JWT для logout.

## Эндпоинты
Все ошибки возвращаются в формате RFC 7807 и содержат `correlation_id`:

```json
{
  "type": "https://parking-slots.local/problems/booking_conflict",
  "title": "Слот уже занят",
  "status": 409,
  "detail": "Слот уже забронирован на выбранную дату",
  "instance": "/api/v1/bookings",
  "code": "BOOKING_CONFLICT",
  "correlation_id": "4d503dd3-2c7f-4e0c-9d47-0c0df127f8e3",
  "errors": {
    "slot_id": ["занят"],
    "booking_date": ["дата недоступна"]
  }
}
```

### Системные
- `GET /health` – проверка живости сервиса.

### Аутентификация (`/api/v1/auth`)
- `POST /register` – создать пользователя.
- `POST /login` – получить bearer-токен.
- `POST /logout` – отозвать токен (добавляет его `jti` в deny-list).

### Ресурс `items` (`/api/v1/items`)
- `GET /api/v1/items?limit=&offset=` – пагинированный список предметов текущего пользователя (`admin` видит все).
- `POST /api/v1/items` – создать предмет, владелец = текущий пользователь.
- `GET /api/v1/items/{item_id}` – получить предмет (владелец или `admin`).
- `PATCH /api/v1/items/{item_id}` – обновить описание (владелец или `admin`).
- `DELETE /api/v1/items/{item_id}` – удалить (владелец или `admin`).

### Бронирования (`/api/v1/bookings`)
- `GET /` – список бронирований пользователя или его предметов (`admin` видит все).
- `POST /` – создать бронирование (конфликт проверяется, доступность учитывается).
- `GET /{booking_id}` – детали (создатель, владелец предмета или `admin`).
- `PUT /{booking_id}` – изменить статус (владелец предмета или `admin`; отменить также может автор).
- `DELETE /{booking_id}` – отменить (меняет статус на `cancelled`).

### Доступность (`/api/v1/availability`)
- `GET` с параметрами `target_date` и опциональным `code` – возвращает список мест и флаг доступности.

## Тесты
```bash
pytest -q
```
Фикстуры используют отдельный SQLite-файл `test_app.db` и автоматически отключают rate-limit. Покрытие включает негативные сценарии: повторная регистрация, конфликт бронирования, запреты доступа и проверку дат.

## Контроли безопасного кодирования (P06)
- **Валидация и нормализация ввода.** Все входные данные проверяются Pydantic-схемами с кастомными валидаторами (например, проверка пароля на длину в байтах и запрет дат в прошлом). Негативные сценарии зафиксированы в тестах `tests/test_auth.py::test_register_password_exceeds_bcrypt_limit` и `tests/test_bookings.py::test_booking_validation_rejects_past_date`.
- **Ошибки в формате RFC 7807.** Пользовательские и системные ошибки конвертируются в problem-details через `app/core/exceptions.py`, добавляя `correlation_id` и карту ошибок. Формат покрыт тестами `tests/test_items.py::test_item_conflict_returns_structured_error` и `tests/test_auth.py::test_login_invalid_password`.
- **Параметризация SQL.** Доступ к SQLite реализован через параметризованные запросы (`app/core/database.py`), что исключает конкатенацию строк. Конфликтные сценарии (например, повторное бронирование) проверяются в `tests/test_bookings.py::test_create_booking_and_conflict_detection`.
- **Секреты из окружения.** JWT секрет (`JWT_SECRET_KEY`) обязателен и валидируется при старте приложения (`app/auth/jwt_handler.py`). Тестовый раннер задаёт безопасное значение в `tests/conftest.py`, а README содержит инструкции по генерации ключа.

Дополнительно включено ограничение частоты запросов (`app/middleware/rate_limit.py`), которое можно отключить в дев-режиме через `DISABLE_RATE_LIMIT`.

## Примеры запросов
```bash
http POST :8000/api/v1/auth/register email=demo@example.com full_name="Demo" password="Password1!"
http POST :8000/api/v1/auth/login email=demo@example.com password="Password1!"
http POST :8000/api/v1/items "Authorization:Bearer <token>" code=S1 description="Near entrance"
http GET  :8000/api/v1/items "Authorization:Bearer <token>" limit==10 offset==0
http POST :8000/api/v1/bookings "Authorization:Bearer <token>" slot_id=1 booking_date=2024-12-31
http POST :8000/api/v1/auth/logout "Authorization:Bearer <token>"
```

### Роли и администрация
- По умолчанию все зарегистрированные пользователи получают роль `user`.
- Чтобы автоматически создать администратора при старте приложения, задайте переменные окружения `DEFAULT_ADMIN_EMAIL` и `DEFAULT_ADMIN_PASSWORD` (опционально `DEFAULT_ADMIN_FULL_NAME`).
- Администратор может просматривать и изменять любые предметы и бронирования.
