"""
seed.py — первоначальное заполнение базы данных WorkSpot.

Запуск: python seed.py

Скрипт идемпотентен: повторный запуск пропустит уже существующие записи.
"""

import asyncio
import random
import uuid
from datetime import date, time, timedelta

from passlib.context import CryptContext
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User, UserRole
from bookings.models import Booking, BookingStatus
from config import settings
from database import AsyncSessionLocal
from spaces.models import Space, TimeSlot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash(password: str) -> str:
    return _pwd_context.hash(password)


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_USERS = [
    {
        "email": settings.admin_email,
        "password": settings.admin_password,
        "name": "Администратор",
        "role": UserRole.admin,
    },
    {
        "email": "user1@workspot.ru",
        "password": "password123",
        "name": "Иван Петров",
        "role": UserRole.user,
    },
    {
        "email": "user2@workspot.ru",
        "password": "password123",
        "name": "Мария Сидорова",
        "role": UserRole.user,
    },
    {
        "email": "user3@workspot.ru",
        "password": "password123",
        "name": "Алексей Козлов",
        "role": UserRole.user,
    },
]

_SPACES = [
    {
        "name": "Точка кипения",
        "address": "Мясницкая ул., 13",
        "city": "Москва",
        "description": "Современное пространство для работы и мероприятий в самом центре Москвы.",
        "price_per_hour": 500,
        "capacity": 20,
        "amenities": ["wifi", "coffee", "projector"],
        "latitude": 55.7647,
        "longitude": 37.6363,
        "photos": [],
    },
    {
        "name": "Ключ",
        "address": "Берсеневская наб., 6с3",
        "city": "Москва",
        "description": "Уютный коворкинг на берегу Москвы-реки с видом на Кремль.",
        "price_per_hour": 1200,
        "capacity": 10,
        "amenities": ["wifi", "meeting_room", "coffee"],
        "latitude": 55.7455,
        "longitude": 37.6089,
        "photos": [],
    },
    {
        "name": "GrowUp Space",
        "address": "Новослободская ул., 31",
        "city": "Москва",
        "description": "Тихое и уютное пространство для сосредоточенной работы.",
        "price_per_hour": 350,
        "capacity": 5,
        "amenities": ["wifi", "coffee"],
        "latitude": 55.7495,
        "longitude": 37.5860,
        "photos": [],
    },
    {
        "name": "Workstation",
        "address": "Варшавское ш., 9с1",
        "city": "Москва",
        "description": "Большое open-space пространство с удобной парковкой.",
        "price_per_hour": 300,
        "capacity": 50,
        "amenities": ["wifi", "parking", "projector"],
        "latitude": 55.7103,
        "longitude": 37.6217,
        "photos": [],
    },
    {
        "name": "Practicum Hub",
        "address": "Льва Толстого ул., 16",
        "city": "Москва",
        "description": "Премиальный переговорный зал для встреч и переговоров.",
        "price_per_hour": 1500,
        "capacity": 2,
        "amenities": ["wifi", "coffee", "meeting_room"],
        "latitude": 55.7337,
        "longitude": 37.5875,
        "photos": [],
    },
]

# 12 слотов в день: 09:00–21:00 по часу
_SLOT_HOURS = list(range(9, 21))  # 9, 10, ..., 20


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


async def seed_users(db: AsyncSession) -> list[User]:
    """Создаёт пользователей, пропускает существующих."""
    created: list[User] = []
    for data in _USERS:
        result = await db.execute(select(User).where(User.email == data["email"]))
        existing = result.scalar_one_or_none()
        if existing:
            created.append(existing)
            continue
        user = User(
            id=uuid.uuid4(),
            email=data["email"],
            hashed_password=_hash(data["password"]),
            name=data["name"],
            role=data["role"],
        )
        db.add(user)
        created.append(user)
    await db.flush()
    return created


async def seed_spaces(db: AsyncSession) -> list[Space]:
    """Создаёт коворкинги, пропускает существующие (по имени)."""
    created: list[Space] = []
    for data in _SPACES:
        result = await db.execute(select(Space).where(Space.name == data["name"]))
        existing = result.scalar_one_or_none()
        if existing:
            created.append(existing)
            continue
        space = Space(
            id=uuid.uuid4(),
            name=data["name"],
            address=data["address"],
            city=data["city"],
            description=data["description"],
            price_per_hour=data["price_per_hour"],
            capacity=data["capacity"],
            amenities=data["amenities"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            photos=data["photos"],
        )
        db.add(space)
        created.append(space)
    await db.flush()
    return created


async def seed_slots(db: AsyncSession, spaces: list[Space]) -> list[TimeSlot]:
    """
    Генерирует 12 слотов/день × 14 дней для каждого коворкинга.
    Пропускает уже существующие (по space_id + date + time_from).
    Помечает ~20% слотов is_booked=True.
    """
    today = date.today()
    all_slots: list[TimeSlot] = []

    for space in spaces:
        for day_offset in range(14):
            slot_date = today + timedelta(days=day_offset)
            for hour in _SLOT_HOURS:
                time_from = time(hour, 0)
                time_to = time(hour + 1, 0)

                # Idempotency check
                result = await db.execute(
                    select(TimeSlot).where(
                        and_(
                            TimeSlot.space_id == space.id,
                            TimeSlot.date == slot_date,
                            TimeSlot.time_from == time_from,
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    all_slots.append(existing)
                    continue

                slot = TimeSlot(
                    id=uuid.uuid4(),
                    space_id=space.id,
                    date=slot_date,
                    time_from=time_from,
                    time_to=time_to,
                    is_booked=random.random() < 0.2,
                )
                db.add(slot)
                all_slots.append(slot)

    await db.flush()
    return all_slots


async def seed_bookings(
    db: AsyncSession,
    users: list[User],
    slots: list[TimeSlot],
) -> list[Booking]:
    """
    Создаёт 5–7 броней для тестовых пользователей (user1, user2, user3).
    Использует только свободные слоты из числа созданных.
    """
    # Только тестовые пользователи (не admin)
    test_users = [u for u in users if u.role == UserRole.user]
    if not test_users:
        return []

    # Свободные слоты (is_booked=False и ещё не занятые в этой же сессии)
    free_slots = [s for s in slots if not s.is_booked]
    if not free_slots:
        return []

    random.shuffle(free_slots)
    target_count = random.randint(5, 7)
    slots_to_book = free_slots[: min(target_count, len(free_slots))]

    created: list[Booking] = []
    for i, slot in enumerate(slots_to_book):
        # Проверяем что слот ещё не забронирован (в БД)
        result = await db.execute(
            select(Booking).where(Booking.slot_id == slot.id)
        )
        if result.scalar_one_or_none():
            continue

        owner = test_users[i % len(test_users)]

        booking = Booking(
            id=uuid.uuid4(),
            user_id=owner.id,
            space_id=slot.space_id,
            slot_id=slot.id,
            status=BookingStatus.active,
        )
        slot.is_booked = True
        db.add(booking)
        created.append(booking)

    await db.flush()
    return created


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            print("🌱 Запуск заполнения базы данных WorkSpot...")

            users = await seed_users(db)
            print(f"   Пользователи:  {len(users)}")

            spaces = await seed_spaces(db)
            print(f"   Коворкинги:    {len(spaces)}")

            slots = await seed_slots(db, spaces)
            print(f"   Слоты:         {len(slots)}")

            bookings = await seed_bookings(db, users, slots)
            print(f"   Бронирования:  {len(bookings)}")

        print(
            f"\n✅ Создано пользователей: {len(users)}, "
            f"коворкингов: {len(spaces)}, "
            f"слотов: {len(slots)}, "
            f"броней: {len(bookings)}"
        )
        print("\n📋 Тестовые аккаунты:")
        print(f"   {settings.admin_email} / {settings.admin_password}  (администратор)")
        print("   user1@workspot.ru / password123")
        print("   user2@workspot.ru / password123")
        print("   user3@workspot.ru / password123")


if __name__ == "__main__":
    asyncio.run(main())
