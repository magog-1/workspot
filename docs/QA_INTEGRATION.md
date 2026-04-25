# QA tooling integration

Этот документ описывает интегрированные в проект инструменты контроля качества и
действия, которые нельзя автоматизировать через коммит в репозиторий.

## Что добавлено в репозиторий

| Компонент | Файл(ы) |
| --- | --- |
| Конфигурация Ruff | `ruff.toml` |
| Зависимости разработчика | `requirements-dev.txt` |
| Конфигурация pytest | `pytest.ini` |
| Тестовая инфраструктура | `tests/conftest.py`, `tests/test_*.py` |
| Pre-commit | `.pre-commit-config.yaml` |
| GitHub Actions CI | `.github/workflows/ci.yml` |
| GitHub Actions PR Quality Gate | `.github/workflows/pr-check.yml` |

## Локальный запуск

```bash
pip install -r requirements-dev.txt

# Lint и форматирование
ruff check .
ruff format --check .

# Тесты без БД (быстрые, не требуют Postgres)
pytest -m "not integration"

# Полный набор (требует поднятого Postgres из docker-compose, либо CI)
pytest
```

Интеграционные тесты помечены маркером `integration` (см. `pytest.ini`) и
требуют доступа к PostgreSQL по адресу из переменной окружения `DATABASE_URL`
(по умолчанию `postgresql+asyncpg://postgres:test@localhost:5433/workspot_test`).

## Pre-commit

```bash
pip install pre-commit
pre-commit install
```

После этого Ruff (lint + format) и базовые проверки запускаются перед каждым
коммитом.

## Что нельзя сделать через коммит — ручные шаги в GitHub

Эти настройки нужно применить вручную в интерфейсе репозитория WorkSpot-FA/workspot.

### Branch protection (Settings → Branches)

Добавить правило для ветки `master` (или `main`/`develop`, если используются):

- ✅ Require status checks to pass before merging
  - `Ruff Lint`
  - `pytest + Coverage`
  - `Quality Gate`
- ✅ Require branches to be up to date before merging
- ✅ Do not allow bypassing the above settings

### Secrets & variables (Settings → Secrets and variables → Actions)

CI-пайплайн читает значения из `env:` блоков workflow и не требует секретов
для прохождения тестов с PostgreSQL-сервисом, описанным в `ci.yml`. Если в
будущем понадобится подключать staging-окружение или сторонние сервисы —
нужно будет добавить соответствующие секреты (`SECRET_KEY`, `DATABASE_URL` и
т. д.) в этот раздел.

## Ограничения текущей реализации

- Модели используют Postgres-специфичные типы (`ARRAY`, `UUID`), поэтому
  интеграционные тесты невозможно запустить на SQLite. Локально нужен Postgres.
- Coverage порог в `pytest.ini` не задан, чтобы CI не блокировался до
  полной написанной интеграции тестов. Целевые показатели описаны в плане:
  `auth ≥ 80%`, `bookings ≥ 75%`, `spaces ≥ 75%`, `users ≥ 70%`.
- `seed.py` исключён из строгих правил Ruff (см. `[lint.per-file-ignores]`).
