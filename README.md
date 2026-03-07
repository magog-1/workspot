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
