import datetime
import uuid

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from spaces.models import Space, TimeSlot
from spaces.schemas import SpaceFilter

# ---------------------------------------------------------------------------
# Spaces
# ---------------------------------------------------------------------------

_SLOT_START_HOUR = 9   # 09:00
_SLOT_END_HOUR = 21    # last slot starts at 20:00 → ends 21:00


async def get_all(db: AsyncSession, filters: SpaceFilter) -> list[Space]:
    query = select(Space)

    # city — exact match (skip if empty, e.g. admin view)
    if filters.city:
        query = query.where(Space.city == filters.city)

    # price_max
    if filters.price_max is not None:
        query = query.where(Space.price_per_hour <= filters.price_max)

    # capacity — minimum
    if filters.capacity is not None:
        query = query.where(Space.capacity >= filters.capacity)

    # amenities — space must contain ALL requested amenities (@> operator)
    if filters.amenities:
        query = query.where(Space.amenities.contains(filters.amenities))

    # date — at least one free slot exists for that date
    if filters.date is not None:
        free_slot = (
            select(TimeSlot.id)
            .where(
                and_(
                    TimeSlot.space_id == Space.id,
                    TimeSlot.date == filters.date,
                    TimeSlot.is_booked == False,  # noqa: E712
                )
            )
            .correlate(Space)
        )
        query = query.where(exists(free_slot))

    query = query.order_by(Space.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, space_id: uuid.UUID) -> Space | None:
    result = await db.execute(select(Space).where(Space.id == space_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, **kwargs) -> Space:
    space = Space(id=uuid.uuid4(), **kwargs)
    db.add(space)
    await db.flush()
    await db.refresh(space)
    return space


async def update(db: AsyncSession, space_id: uuid.UUID, **kwargs) -> Space | None:
    space = await get_by_id(db, space_id)
    if space is None:
        return None
    for key, value in kwargs.items():
        setattr(space, key, value)
    await db.flush()
    await db.refresh(space)
    return space


async def delete(db: AsyncSession, space_id: uuid.UUID) -> None:
    space = await get_by_id(db, space_id)
    if space:
        await db.delete(space)
        await db.flush()


# ---------------------------------------------------------------------------
# TimeSlots
# ---------------------------------------------------------------------------


async def get_slots(
    db: AsyncSession, space_id: uuid.UUID, slot_date: datetime.date
) -> list[TimeSlot]:
    result = await db.execute(
        select(TimeSlot)
        .where(
            and_(
                TimeSlot.space_id == space_id,
                TimeSlot.date == slot_date,
            )
        )
        .order_by(TimeSlot.time_from)
    )
    return list(result.scalars().all())


async def generate_slots(
    db: AsyncSession,
    space_id: uuid.UUID,
    date_from: datetime.date,
    date_to: datetime.date,
) -> int:
    """Generate hourly slots 09:00–21:00 for each day in [date_from, date_to].

    Skips slots that already exist (by space_id + date + time_from).
    Returns the count of newly created slots.
    """
    # Fetch existing slots in the date range to avoid duplicates
    existing_result = await db.execute(
        select(TimeSlot.date, TimeSlot.time_from).where(
            and_(
                TimeSlot.space_id == space_id,
                TimeSlot.date >= date_from,
                TimeSlot.date <= date_to,
            )
        )
    )
    existing_keys: set[tuple] = {(row.date, row.time_from) for row in existing_result}

    created = 0
    current_date = date_from
    delta = datetime.timedelta(days=1)

    while current_date <= date_to:
        for hour in range(_SLOT_START_HOUR, _SLOT_END_HOUR):
            t_from = datetime.time(hour, 0)
            t_to = datetime.time(hour + 1, 0)
            if (current_date, t_from) in existing_keys:
                continue
            slot = TimeSlot(
                id=uuid.uuid4(),
                space_id=space_id,
                date=current_date,
                time_from=t_from,
                time_to=t_to,
                is_booked=False,
            )
            db.add(slot)
            created += 1
        current_date += delta

    if created:
        await db.flush()
    return created


async def add_photo(
    db: AsyncSession, space_id: uuid.UUID, photo_path: str
) -> Space | None:
    space = await get_by_id(db, space_id)
    if space is None:
        return None
    current_photos: list[str] = list(space.photos or [])
    current_photos.append(photo_path)
    space.photos = current_photos
    await db.flush()
    await db.refresh(space)
    return space
