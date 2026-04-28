# ReZeb — AI-платформа строительного контроля

[![CI](https://github.com/in3gun33/rezeb/actions/workflows/ci.yml/badge.svg)](https://github.com/in3gun33/rezeb/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/next.js-15-black.svg)](https://nextjs.org/)

AI-powered SaaS для строительной отрасли. Два модуля: автоматический контроль качества строительных работ (фото → дефекты → НТД) и интеллектуальный подбор материалов по запросам ПТО.

---

## Содержание

- [Возможности](#возможности)
- [Технологический стек](#технологический-стек)
- [Быстрый старт](#быстрый-старт)
- [Переменные окружения](#переменные-окружения)
- [Разработка](#разработка)
- [API](#api)
- [Архитектура](#архитектура)
- [Деплой](#деплой)
- [Дорожная карта](#дорожная-карта)

---

## Возможности

### Ассистент контроля
- Загрузка фотографий строительных конструкций с валидацией качества (Laplacian blur, ArUco-маркеры)
- Автоматическое определение типа конструкции и обнаружение дефектов (YOLOv11 + Claude Sonnet 4.6)
- Классификация дефектов по критичности: **допустимый / значительный / критический**
- Автоматическая привязка дефектов к нормативной базе (ГОСТ, СП, СНиП) через RAG по НТД
- Эскалация на Claude Opus 4.7 при уверенности < 70% или критических дефектах
- Telegram-алерты при обнаружении критических дефектов
- SSE-стрим статуса анализа в реальном времени
- Экспорт протокола в JSON

### Ассистент ПТО
- Нормализация произвольных запросов (Claude Haiku 4.5)
- Гибридный поиск по реестру материалов (pgvector cosine + PostgreSQL FTS + RRF fusion)
- Итоговый подбор с коэффициентом уверенности и указанием аналогов (Claude Sonnet 4.6)
- Импорт реестра из Excel (`.xlsx`) с автоматической дедупликацией (RapidFuzz ≥ 92%)
- Пакетная обработка запросов

### Платформа
- JWT-аутентификация (access 15 мин + refresh 30 дней с ротацией)
- API-ключи для интеграций
- Мониторинг бюджета LLM-вызовов (алерт при 80% месячного лимита, ~30 000 ₽)
- Ролевая модель: `admin` / `engineer` / `viewer`
- Append-only журнал аудита всех действий
- Управление проектами (строительные объекты)
- RAG по нормативной документации (НТД): загрузка PDF/DOCX → векторный поиск

---

## Технологический стек

| Слой | Технология |
|------|-----------|
| **Backend** | FastAPI 0.115 + Python 3.12 (async/await) |
| **ORM / Migrations** | SQLAlchemy 2.0 async + Alembic |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache / Queue** | Redis 7 + arq |
| **File Storage** | S3-compatible (MinIO в dev, любой S3 в prod) |
| **AI / LLM** | [AITUNNEL API](https://aitunnel.ru) — Claude Sonnet/Opus/Haiku, text-embedding-3-large |
| **CV / ML** | YOLOv11 + ONNX Runtime + OpenCV |
| **Frontend** | Next.js 15 + TypeScript + Tailwind CSS + TanStack Query |
| **State** | Zustand |
| **Auth** | JWT, bcrypt, SHA-256 token hashing |
| **Proxy** | Nginx (SSL termination, SSE proxy) |
| **CI/CD** | GitHub Actions → GHCR → SSH deploy |
| **Monitoring** | Sentry (опц.), Telegram-алерты, structlog JSON |

---

## Быстрый старт

### Требования

- **Docker** 24+ и **Docker Compose** v2
- **Git**
- Ключ [AITUNNEL API](https://aitunnel.ru) (для LLM/embeddings)

### Установка

```bash
git clone https://github.com/in3gun33/rezeb.git
cd rezeb

# Скопируй и заполни .env
cp .env.example .env
# Обязательно: укажи AITUNNEL_API_KEY в .env

# Запуск всего стека
make dev
```

После запуска:

| Сервис | URL |
|--------|-----|
| **API docs** (Swagger) | http://localhost:8000/docs |
| **Frontend** | http://localhost:3000 |
| **MinIO console** | http://localhost:9001 |

**Логин по умолчанию**: `admin@rezeb.ru` / `Admin123!`

> MinIO credentials: `minioadmin` / `minioadmin`

---

## Переменные окружения

Полный пример: [`.env.example`](.env.example)

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `AITUNNEL_API_KEY` | **Да** | API ключ AITUNNEL для LLM и эмбеддингов |
| `DATABASE_URL` | Да | PostgreSQL asyncpg URL |
| `REDIS_URL` | Да | Redis URL для rate limiting и кэша |
| `REDIS_QUEUE_URL` | Да | Redis URL для arq очереди заданий |
| `APP_SECRET_KEY` | Да | Секрет приложения |
| `JWT_SECRET_KEY` | Да | Секрет для подписи JWT токенов |
| `S3_ENDPOINT_URL` | Да | S3 / MinIO endpoint |
| `S3_ACCESS_KEY` | Да | S3 access key |
| `S3_SECRET_KEY` | Да | S3 secret key |
| `APP_ENV` | Нет | `development` (по умол.) / `production` |
| `TELEGRAM_BOT_TOKEN` | Нет | Бот для алертов о критических дефектах |
| `TELEGRAM_ALERT_CHAT_ID` | Нет | Chat ID для Telegram-алертов |
| `SENTRY_DSN` | Нет | DSN для Sentry error tracking |
| `MONTHLY_LLM_BUDGET_RUB` | Нет | Лимит LLM-расходов в месяц, ₽ (по умол. 30 000) |
| `CORS_ORIGINS` | Нет | Через запятую, по умол. `http://localhost:3000` |

---

## Разработка

### Команды Make

```bash
make dev              # Запустить весь стек (docker compose up --build)
make up               # Запустить без пересборки
make down             # Остановить
make logs             # Смотреть логи всех сервисов
make logs-api         # Логи только API
make test             # pytest (backend)
make lint             # ruff check + mypy
make format           # ruff format + ruff check --fix
make migrate          # alembic upgrade head
make migrate-create msg=<name>  # Создать новую миграцию
make seed             # Заполнить БД тестовыми данными
make shell-api        # bash внутри контейнера api
make shell-db         # psql в контейнере postgres
```

### Структура репозитория

```
ReZeb/
├── backend/                  # FastAPI Python 3.12 monolith
│   ├── app/
│   │   ├── core/             # config, security, aitunnel, queue, ratelimit, telegram
│   │   ├── db/               # SQLAlchemy base, session factory, model imports
│   │   ├── modules/
│   │   │   ├── auth/         # JWT, roles, refresh tokens, API keys, profile
│   │   │   ├── control/      # Сессии анализа, фото, дефекты, SSE
│   │   │   ├── pto/          # Запросы ПТО, реестр материалов, гибридный поиск
│   │   │   ├── ntd/          # НТД документы, клаузы, RAG
│   │   │   ├── projects/     # Строительные объекты
│   │   │   ├── audit/        # Журнал аудита (append-only)
│   │   │   ├── media/        # S3 upload/download
│   │   │   └── registry/     # CLI-индексер эмбеддингов
│   │   ├── workers/          # arq background worker
│   │   └── main.py           # FastAPI entrypoint
│   ├── alembic/              # Миграции БД
│   ├── scripts/              # seed_dev_data.py, init_db.sql
│   └── tests/                # pytest
├── frontend/                 # Next.js 15 + TypeScript
│   └── src/
│       ├── app/              # App Router pages (login, dashboard/*)
│       ├── components/       # Sidebar, Toast UI
│       ├── hooks/            # useControl, usePTO, useProjects
│       ├── lib/              # Axios API client с auth interceptor
│       ├── stores/           # Zustand auth store
│       └── types/            # TypeScript типы
├── ml_service/               # YOLO inference (stub в dev, GPU-сервис в prod)
├── nginx/                    # nginx.conf с SSL и SSE proxy
├── docker-compose.yml        # Dev стек
├── docker-compose.prod.yml   # Prod стек (без MinIO, с nginx)
└── Makefile
```

### База данных

PostgreSQL 16 + pgvector. Схемы БД:

| Схема | Содержит |
|-------|---------|
| `auth` | users, refresh_tokens, api_keys, projects |
| `control` | sessions, photos, defects |
| `pto` | registry, synonyms, queries |
| `ntd` | documents, clauses |
| `audit` | events (append-only trigger) |

После первого запуска:
```bash
make migrate   # применить миграции
make seed      # создать admin + тестовые данные
```

Для индексирования эмбеддингов реестра ПТО:
```bash
docker compose exec api python -m app.modules.registry.indexer
```

### Работа с LLM

Все LLM-вызовы идут через **AITUNNEL** (OpenAI-compatible API, рублёвый биллинг):

| Модель | Использование |
|--------|--------------|
| `claude-sonnet-4-6` | Анализ фото, финальный матчинг ПТО, RAG |
| `claude-opus-4-7` | Эскалация (confidence < 0.7 или critical дефект) |
| `claude-haiku-4-5-20251001` | Нормализация текста ПТО |
| `text-embedding-3-large` | Векторные эмбеддинги (3072 dim) |

Prompt caching через `cache_control: ephemeral` снижает расходы на input tokens на 70–90%.

---

## API

OpenAPI Swagger: http://localhost:8000/docs (только в dev-режиме)

### Ключевые эндпоинты

#### Аутентификация
```
POST /api/v1/auth/register          — регистрация
POST /api/v1/auth/login             — вход (JWT)
POST /api/v1/auth/refresh           — обновление токена
POST /api/v1/auth/logout            — выход
GET  /api/v1/auth/me                — текущий пользователь
POST /api/v1/auth/forgot-password   — запрос сброса пароля
POST /api/v1/auth/reset-password    — смена пароля по токену
PATCH /api/v1/auth/profile          — обновление профиля
POST /api/v1/auth/profile/change-password — смена пароля
POST /api/v1/auth/api-keys          — создать API ключ
GET  /api/v1/auth/api-keys          — список API ключей
DELETE /api/v1/auth/api-keys/{id}   — отозвать API ключ
```

#### Ассистент контроля
```
POST /api/v1/control/sessions                     — создать сессию анализа
GET  /api/v1/control/sessions                     — список сессий
GET  /api/v1/control/sessions/{id}                — детали сессии
POST /api/v1/control/sessions/{id}/photos         — загрузить фото
POST /api/v1/control/sessions/{id}/analyze        — запустить анализ
GET  /api/v1/control/sessions/{id}/events         — SSE стрим статуса
GET  /api/v1/control/sessions/{id}/photos/{pid}/url — presigned URL фото
GET  /api/v1/control/sessions/{id}/export         — экспорт протокола JSON
```

#### Ассистент ПТО
```
POST /api/v1/pto/queries              — создать запрос ПТО
GET  /api/v1/pto/queries/{id}         — результат запроса
GET  /api/v1/pto/registry/search      — поиск по реестру
POST /api/v1/pto/registry/import      — импорт реестра из Excel
GET  /api/v1/pto/registry             — список реестра (пагинация)
GET  /api/v1/pto/registry/categories  — список категорий
GET  /api/v1/pto/registry/{id}        — элемент реестра
```

#### НТД
```
GET  /api/v1/ntd/documents    — список документов
POST /api/v1/ntd/documents    — загрузить документ (PDF/DOCX)
GET  /api/v1/ntd/search       — поиск по клаузам (?q=...)
```

#### Прочее
```
GET  /api/v1/projects                  — проекты пользователя
POST /api/v1/projects                  — создать проект
GET  /api/v1/audit/events              — журнал аудита (admin)
GET  /api/v1/admin/users               — управление пользователями (admin)
GET  /api/v1/admin/stats               — статистика (admin)
GET  /api/v1/admin/costs               — расходы LLM (admin)
GET  /health                           — healthcheck (DB + Redis)
```

---

## Архитектура

### Диаграмма потока (Ассистент контроля)

```
Пользователь
    │
    ▼
[Next.js Frontend]
    │  POST /control/sessions/{id}/photos
    ▼
[FastAPI API]
    │  1. Валидация фото (blur, ArUco)
    │  2. Сохранение в S3
    │  3. Постановка в очередь arq
    ▼
[arq Worker]
    │  1. YOLO inference (ml-service)
    │  2. RAG по НТД (pgvector)
    │  3. LLM анализ (Claude Sonnet)
    │  4. Эскалация если нужно (Claude Opus)
    │  5. Telegram-алерт при critical
    ▼
[PostgreSQL]     [Redis]     [S3/MinIO]
```

### Гибридный поиск ПТО (RRF Fusion)

```
Запрос пользователя
    │
    ├─► Haiku: нормализация текста
    │
    ├─► pgvector: косинусное сходство (text-embedding-3-large, 3072 dim)
    │
    ├─► PostgreSQL FTS: полнотекстовый поиск (tsvector, russian)
    │
    ├─► RRF Fusion: объединение рангов (k=60)
    │
    └─► Sonnet: финальный подбор + коэффициент уверенности
```

### Оптимизация стоимости LLM

- **Prompt caching** (`cache_control: ephemeral`): экономия 70–90% на повторных системных промптах
- **Трекинг стоимости** каждого вызова (`cost_rub` в таблицах control.sessions и pto.queries)
- **Daily лимиты** на пользователя (по умолчанию: 50 сессий контроля, 200 ПТО запросов)
- **Бюджетный алерт** при достижении 80% месячного лимита

---

## Деплой

### Production (1 VM)

Требования: 4 vCPU / 8 GB RAM, Docker, Managed PostgreSQL, Managed Redis, S3.

```bash
# На prod VM
git clone https://github.com/in3gun33/rezeb.git /opt/rezeb
cd /opt/rezeb

cp .env.example .env
# Заполни .env для production (APP_ENV=production, реальные DB/Redis/S3)

docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api python scripts/seed_dev_data.py
```

### CI/CD (GitHub Actions)

Push в ветку `main` автоматически:
1. Собирает Docker образы (`api`, `frontend`)
2. Пушит в GitHub Container Registry (GHCR)
3. Деплоит на VM через SSH

Необходимые GitHub Secrets:
- `PROD_HOST` — IP/hostname production сервера
- `PROD_USER` — SSH пользователь
- `PROD_SSH_KEY` — приватный SSH ключ

### Индексирование эмбеддингов (первый запуск)

После импорта реестра ПТО из Excel запусти индексер эмбеддингов:

```bash
docker compose exec api python -m app.modules.registry.indexer
```

---

## Дорожная карта

| Этап | Статус |
|------|--------|
| Stage 0: Dev-окружение | ✅ Готово |
| Stage 1: Auth + S3 + Audit | ✅ Готово |
| Stage 2: ПТО модуль | ✅ Готово |
| Stage 3: Control модуль | ✅ Готово |
| Stage 4: НТД + Проекты | ✅ Готово |
| Stage 5: CI/CD + Production | ✅ Готово |
| Stage 6: Pilot-тестирование | 🔄 В процессе |

### Post-MVP (не включено в MVP)
- ERP-интеграции (1C / SAP)
- Электронная подпись
- Нативное мобильное приложение
- Режим «до/после» (сравнение фото)
- Multi-tenancy (организации)
- bge-reranker для ПТО поиска
- ФСТЭК-сертификация

---

## Лицензия

MIT — см. [LICENSE](LICENSE).
