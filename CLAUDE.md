# ReZeb — AI-платформа строительного контроля

## Описание проекта

ReZeb — AI-powered SaaS для строительной отрасли с двумя модулями:
1. **Ассистент контроля** — визуальный анализ фото конструкций (YOLOv11 + Claude Sonnet 4.6)
2. **Ассистент ПТО** — автоматический подбор материалов из реестра (hybrid search + LLM)

## Структура репозитория

```
ReZeb/
├── backend/          # FastAPI Python 3.12 monolith
│   ├── app/
│   │   ├── core/     # config, security, aitunnel client, queue, ratelimit
│   │   ├── db/       # SQLAlchemy base, session factory
│   │   ├── modules/  # auth, control, pto, ntd, audit, media, projects, registry
│   │   ├── workers/  # arq background worker
│   │   └── main.py   # FastAPI app entrypoint
│   ├── alembic/      # DB migrations
│   ├── scripts/      # seed_dev_data.py
│   └── tests/        # pytest
├── frontend/         # Next.js 15 + TypeScript
│   └── src/
│       ├── app/      # App Router pages
│       ├── components/
│       ├── hooks/    # useControl, usePTO, useProjects
│       ├── lib/      # axios api client
│       ├── stores/   # Zustand auth store
│       └── types/    # TypeScript types
├── ml_service/       # YOLO inference stub (dev) / real GPU service (prod)
├── docker-compose.yml
└── Makefile
```

## Быстрый старт

```bash
cp .env.example .env
# Заполни AITUNNEL_API_KEY в .env
make dev          # запустить весь стек
# API:      http://localhost:8000/docs
# Frontend: http://localhost:3000
# MinIO:    http://localhost:9001 (minioadmin/minioadmin)
```

**Default admin**: `admin@rezeb.ru` / `Admin123!`

## Команды

```bash
make migrate              # alembic upgrade head
make migrate-create msg=name  # новая миграция
make test                 # pytest
make lint                 # ruff + mypy
make shell-api            # bash в контейнере api
make shell-db             # psql
```

## Переменные окружения (ключевые)

| Переменная | Описание |
|---|---|
| `AITUNNEL_API_KEY` | API ключ AITUNNEL (обязателен для LLM/embeddings) |
| `DATABASE_URL` | PostgreSQL asyncpg URL |
| `REDIS_URL` | Redis URL для rate limiting |
| `REDIS_QUEUE_URL` | Redis URL для arq очереди |
| `S3_*` | S3/MinIO параметры |
| `TELEGRAM_BOT_TOKEN` | Telegram бот для алертов (опционально) |
| `SENTRY_DSN` | Sentry DSN (опционально) |

## Архитектурные решения

### LLM модели (via AITUNNEL)
- `claude-sonnet-4-6` — анализ фото, финальный матчинг ПТО, RAG
- `claude-opus-4-7` — эскалация при confidence < 0.7 или critical дефекте
- `claude-haiku-4-5-20251001` — нормализация текста ПТО
- `text-embedding-3-large` — векторные эмбеддинги (3072 dim)

### Оптимизация стоимости LLM
- Prompt caching через `cache_control: ephemeral` (экономия 70-90% на input tokens)
- Трекинг стоимости каждого вызова в БД (`cost_rub` поле)
- Daily лимиты на пользователя (`daily_control_limit_per_user`, `daily_pto_limit_per_user`)
- Бюджетный алерт при 80% месячного лимита

### Hybrid search (PTO)
- pgvector cosine similarity + Postgres FTS
- RRF fusion (Reciprocal Rank Fusion, k=60)
- bge-reranker планируется в post-MVP

### Escalation (Control)
- Если `construction_type_confidence < 0.7` ИЛИ есть critical дефект → повторный вызов Opus 4.7
- Telegram алерт при critical дефектах

## База данных

PostgreSQL 16 + pgvector. Схемы: `auth`, `control`, `pto`, `ntd`, `audit`.

Миграции: `alembic upgrade head`
После импорта реестра проиндексировать эмбеддинги: `python -m app.modules.registry.indexer`

## Deployment (prod)

1 VM (4vCPU/8GB) + GPU VM (T4) + Managed PostgreSQL + Managed Redis + S3
Docker Compose → Watchtower auto-deploy

```bash
# На prod VM
docker compose -f docker-compose.yml up -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_dev_data.py
```

## API

OpenAPI docs: http://localhost:8000/docs (только dev)

Ключевые эндпоинты:
- `POST /api/v1/auth/login` — получить JWT
- `POST /api/v1/control/sessions` — создать сессию анализа
- `POST /api/v1/control/sessions/{id}/photos` — загрузить фото
- `POST /api/v1/control/sessions/{id}/analyze` — запустить анализ
- `GET /api/v1/control/sessions/{id}/events` — SSE stream статуса
- `POST /api/v1/pto/queries` — запрос ПТО
- `POST /api/v1/pto/registry/import` — импорт реестра Excel
- `GET /api/v1/ntd/search?q=...` — RAG поиск по НТД
- `GET /health` — health check (DB + Redis)

## Ограничения MVP

Согласно ТЗ в MVP не реализованы:
- ERP интеграции (1C/SAP)
- Электронная подпись
- ФСТЭК сертификация
- Нативное мобильное приложение
- Режим "до/после" (сравнение)
- Multi-tenancy (организации) — планируется в post-MVP

## Дорожная карта

| Этап | Статус |
|---|---|
| Stage 0: Dev environment | ✅ Готово |
| Stage 1: Registry import + migrations | ✅ Готово |
| Stage 2: ML integration + admin panel | ✅ Готово |
| Stage 3: NTD RAG + export | ✅ Готово |
| Stage 4: Projects + audit + hooks | ✅ Готово |
| Stage 5: Pilot testing | 🔄 В процессе |
