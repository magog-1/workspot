import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import spaces.repository as repo
from spaces.models import Space, TimeSlot
from spaces.schemas import SpaceFilter, SpaceResponse, SlotResponse


async def get_all(db: AsyncSession, filters: SpaceFilter) -> list[Space]:
    return await repo.get_all(db, filters)


async def get_space_or_404(db: AsyncSession, space_id: uuid.UUID) -> Space:
    space = await repo.get_by_id(db, space_id)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Коворкинг {space_id} не найден",
        )
    return space


async def create_space(db: AsyncSession, **kwargs) -> Space:
    return await repo.create(db, **kwargs)


async def update_space(
    db: AsyncSession, space_id: uuid.UUID, **kwargs
) -> Space:
    space = await repo.update(db, space_id, **kwargs)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Коворкинг {space_id} не найден",
        )
    return space


async def delete_space(db: AsyncSession, space_id: uuid.UUID) -> None:
    await get_space_or_404(db, space_id)
    await repo.delete(db, space_id)


async def get_slots(
    db: AsyncSession, space_id: uuid.UUID, slot_date: datetime.date
) -> list[TimeSlot]:
    await get_space_or_404(db, space_id)
    return await repo.get_slots(db, space_id, slot_date)


async def generate_slots(
    db: AsyncSession, space_id: uuid.UUID, date_from: datetime.date, date_to: datetime.date
) -> int:
    await get_space_or_404(db, space_id)
    return await repo.generate_slots(db, space_id, date_from, date_to)


async def add_photo(
    db: AsyncSession, space_id: uuid.UUID, photo_path: str
) -> Space:
    space = await repo.add_photo(db, space_id, photo_path)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Коворкинг {space_id} не найден",
        )
    return space


def spaces_to_map_json(spaces: list[Space]) -> list[dict]:
    """Convert Space ORM list to a minimal list of dicts for Yandex Maps JS."""
    result = []
    for s in spaces:
        result.append(
            {
                "id": str(s.id),
                "name": s.name,
                "address": s.address,
                "price_per_hour": float(s.price_per_hour),
                "latitude": s.latitude,
                "longitude": s.longitude,
            }
        )
    return result
