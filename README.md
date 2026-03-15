# WorkSpot

Платформа для поиска и бронирования коворкингов в Москве.

Стек: **FastAPI** · **PostgreSQL** · **SQLAlchemy (async)** · **Jinja2** · **Bootstrap 5** · **Яндекс Карты JS API 2.1**

---

## Быстрый старт (Docker)

```bash
cp .env.example .env          # заполни переменные (минимум SECRET_KEY)
docker-compose up --build     # поднимает app + db
docker-compose exec app alembic upgrade head   # применяет миграции
docker-compose exec app python seed.py         # заполняет тестовыми данными
```

Открыть в браузере: <http://localhost:8000>

---

## Локальный запуск без Docker

```bash
pip install -r requirements.txt
# Заполнить .env (DATABASE_URL указать на локальный PostgreSQL)
alembic upgrade head
python seed.py
uvicorn main:app --reload
```

---

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | Строка подключения PostgreSQL | `postgresql+asyncpg://user:pass@db:5432/workspot` |
| `SECRET_KEY` | Секрет для JWT (мин. 32 символа) | `supersecretkey-change-me!!` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access-токена (мин.) | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Время жизни refresh-токена (дни) | `7` |
| `ADMIN_EMAIL` | Email администратора | `admin@workspot.ru` |
| `ADMIN_PASSWORD` | Пароль администратора | `adminpass123` |
| `YANDEX_MAPS_API_KEY` | Ключ Яндекс Карт JS API | *(см. ниже)* |

Все переменные читаются из файла `.env` в корне проекта.

---

## Яндекс Карты

Для отображения карты с маркерами коворкингов необходим API-ключ:

1. Зарегистрироваться на <https://developer.tech.yandex.ru/>
2. Создать ключ: **«JavaScript API и HTTP Геокодер»**
3. Вставить ключ в `.env`:
   ```
   YANDEX_MAPS_API_KEY=ваш_ключ
   ```

> ⚠️ Если `YANDEX_MAPS_API_KEY` не задан или пуст — карта заменяется
> серой заглушкой «Карта недоступна». Список коворкингов, фильтры
> и бронирование продолжают работать в полном объёме.

---

## Тестовые аккаунты (после `python seed.py`)

| Email | Пароль | Роль |
|---|---|---|
| `admin@workspot.ru` | `adminpass123` | Администратор |
| `user1@workspot.ru` | `password123` | Пользователь |
| `user2@workspot.ru` | `password123` | Пользователь |
| `user3@workspot.ru` | `password123` | Пользователь |

---

## Маршруты приложения

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/spaces` | Главная — список коворкингов с фильтрами и картой |
| `GET` | `/spaces/{id}` | Детальная страница коворкинга + бронирование |
| `GET` | `/spaces/{id}/slots?date=YYYY-MM-DD` | JSON: доступные слоты на дату |
| `POST` | `/auth/register` | Регистрация |
| `POST` | `/auth/login` | Вход |
| `GET` | `/auth/logout` | Выход |
| `POST` | `/bookings` | Создать бронирование |
| `GET` | `/bookings/my` | Мои бронирования |
| `POST` | `/bookings/{id}/cancel` | Отменить бронирование |
| `GET` | `/admin/dashboard` | Панель администратора |
| `POST` | `/admin/spaces` | Добавить коворкинг |
| `POST` | `/admin/spaces/{id}/edit` | Редактировать коворкинг |
| `POST` | `/admin/spaces/{id}/delete` | Удалить коворкинг |
| `POST` | `/admin/spaces/{id}/slots` | Сгенерировать слоты |
| `POST` | `/admin/spaces/{id}/photo` | Загрузить фото |

---

## Swagger UI

<http://localhost:8000/docs>

---

## Мониторинг (Prometheus)

В проект добавлены endpoint'ы:

- `GET /healthz` — проверка доступности приложения
- `GET /metrics` — метрики Prometheus (служебный endpoint)

`/metrics` рекомендуется публиковать только во внутренней сети.

### Запуск

```bash
docker-compose up --build
```

Открыть Prometheus: <http://localhost:9090>

### Визуализация в самом Prometheus

В Prometheus можно смотреть метрики в двух режимах:

- **Graph** — график по времени
- **Table** — табличный вид текущих значений

Используйте готовые recording rules:

- `workspot:api_request_p95_seconds` — p95 по API-группам
- `workspot:booking_collision_rate_30d` — collision rate за 30 дней
- `workspot:uptime_24h_percent` — uptime за последние 24 часа, %

Быстрые ссылки:

- p95: <http://localhost:9090/graph?g0.expr=workspot%3Aapi_request_p95_seconds&g0.tab=0>
- collision 30d: <http://localhost:9090/graph?g0.expr=workspot%3Abooking_collision_rate_30d&g0.tab=0>
- uptime 24h %: <http://localhost:9090/graph?g0.expr=workspot%3Auptime_24h_percent&g0.tab=0>

Чтобы видеть историю, установите диапазон времени в правом верхнем углу (например, Last 24 hours / Last 7 days).

### Что измеряется

1. **Доступность (Uptime)**
    - Метрика: `up{job="workspot-app"}`
    - Интервал scrape: `30s`

2. **Время ответа API (p95 latency)**
    - Метрика: `http_request_duration_seconds_bucket`
    - Считается только для API-групп: `/auth`, `/spaces`, `/bookings`, `/users`, `/admin`

3. **Коллизии бронирований (30 дней)**
    - Метрики:
       - `booking_create_attempts_total`
       - `booking_collisions_total`
       - `booking_create_success_total`

### Готовые PromQL-запросы

**p95 latency (по API-группам):**

```promql
histogram_quantile(
   0.95,
   sum by (le, path_group) (
      rate(http_request_duration_seconds_bucket[5m])
   )
)
```

**Collision rate за 30 дней:**

```promql
sum(increase(booking_collisions_total[30d]))
/
clamp_min(sum(increase(booking_create_attempts_total[30d])), 1)
```

### Диапазоны оценки

- Uptime:
   - `>= 99.5%` — норма
   - `98%..99.5%` — требует внимания
   - `< 98%` — критично

- p95 latency:
   - `<= 0.3` сек — норма
   - `0.3..0.8` сек — требует внимания
   - `> 0.8` сек — критично

- Collision rate (30d):
   - `0` — норма
   - `1..2` случаев — расследовать
   - `>= 3` — критично

---

## Структура проекта

```
workspot/
├── auth/            # Регистрация, вход, JWT
├── spaces/          # Коворкинги и временные слоты
├── bookings/        # Бронирования
├── users/           # Профиль пользователя
├── admin/           # Панель администратора
├── templates/       # Jinja2-шаблоны (Bootstrap 5)
│   └── admin/
├── static/
│   └── uploads/     # Загружаемые фото коворкингов
├── migrations/      # Alembic миграции
├── main.py          # Точка входа FastAPI
├── config.py        # Настройки (pydantic-settings)
├── database.py      # Async SQLAlchemy engine
├── seed.py          # Заполнение тестовыми данными
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
