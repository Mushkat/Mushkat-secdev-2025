# SecDev Course Template

Стартовый шаблон для студенческого репозитория (HSE SecDev 2025).

## Быстрый старт
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
uvicorn app.main:app --reload
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

## Описание будущего проекта
### Название
Parking Slots (Mock), Бронирование парковочных мест (без платежей)
### Сущности
"User; Slot(code); Booking(slot_id, date, status)"
### Must endpoints
CRUD /slots; CRUD /bookings; GET /availability
### Security focus
AuthN/AuthZ; owner-only; conflict checks
### Stack
Python/FastAPI + SQLite/Postgres + Pytest

### Примеры использования API

### Получение списка парковочных мест
```bash
curl -X GET "http://localhost:8000/api/v1/slots"
См. также: `SECURITY.md`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`.
```
### Создание бронирования
```bash
curl -X POST "http://localhost:8000/api/v1/booking" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": 1,
    "status": 1,
    "date": "2024-01-15"
  }'
```
### Проверка доступности слота
```bash
curl -X GET "http://localhost:8000/api/v1/availability?target_date=2024-01-15"
```
