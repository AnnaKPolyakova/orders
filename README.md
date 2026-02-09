## Orders

Небольшой сервис на FastAPI с подключением к PostgreSQL и Redis. Предоставляет базовый /ping эндпоинт для проверки доступности зависимостей и готов к дальнейшему развитию (модели, миграции Alembic, Celery/Redis, Nginx).

### Стек
- **FastAPI** (Uvicorn)
- **SQLAlchemy/SQLModel** (async, `asyncpg`)
- **Redis** (async)
- **Pydantic Settings** для конфигурации
- **Alembic** для миграций
- Docker Compose для инфраструктуры (Postgres, Redis, Nginx)

### Структура проекта (основное)
`
src/app/
  services/      # сервисы
  core/          # конфиг и логирование
  db/            # Postgres/Redis клиенты
  models/        # SQLModel (база и сущности)
  api/           # точки расширения API
  main.py        # FastAPI приложение и /ping
tests/         # Тесты
alembic/         # миграции
docker-compose*.yml
Dockerfile
nginx/nginx.conf
`

### Требования
- Python 3.13+
- Poetry 2.x
- (опционально) Docker + Docker Compose

### Установка (локально, без Docker)
`bash
poetry install --no-root
`

### Переменные окружения
Проект читает `.env` (см. `wbbot/core/config.py`). Значения по умолчанию
подставляются, но рекомендуется явно задать их:
`env
PROJECT_NAME=Orders
APP_ENV=dev
APP_LOG_LEVEL=INFO

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PROTOCOL=redis

# Postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD

# Grafana
GF_SECURITY_ADMIN_USER
GF_SECURITY_ADMIN_PASSWORD

### Запуск приложения (локально)
`bash
poetry run python -m src.app.main
# или
poetry run uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
`

После запуска:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- Здоровье сервисов: `GET http://localhost:8000/ping`

Пример ответа `/ping`:
`json
{
  "redis_ping": "pong",
  "postgres_ping": "pong"
}
`

### База данных и миграции (Alembic)
Инициализация (если потребуется):
`bash
alembic init alembic
`

Создать миграции:
`bash
alembic revision --autogenerate -m "add user"
`

Применить миграции:
`bash
alembic upgrade head
`

Обратите внимание: укажите корректный DSN/переменные окружения для
подключения к вашей БД (см. `.env`).

### Запуск инфраструктуры в Docker (Postgres/Redis)
Для локальной разработки достаточно поднять Postgres и Redis:
`bash
docker compose -f docker-compose-local.yml up -d
`

Переменные `.env` должны содержать порты `POSTGRES_PORT` и `REDIS_PORT`,
чтобы пробросы в compose совпали с локальными настройками клиента.


### Тесты
`bash
run pytest -q
`

### Линтеры и форматирование
`bash
poetry run flake8
poetry run isort .
poetry run black .
`

### Полезные ссылки по коду
- Конфигурация: `src/app/core/config.py`
- Инициализация БД/Redis: `src/app/db/postgres.py`,
`src/app/db/redis.py`
- Приложение: `src/app/main.py`

### Лицензия
MIT
