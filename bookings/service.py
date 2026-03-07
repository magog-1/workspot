import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import bookings.repository as repo
from bookings.models import Booking
from bookings.schemas import BookingResponse
from spaces.models import TimeSlot
from sqlalchemy import select


async def get_slot_or_404(db: AsyncSession, slot_id: uuid.UUID) -> TimeSlot:
    result = await db.execute(select(TimeSlot).where(TimeSlot.id == slot_id))
    slot = result.scalar_one_or_none()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Слот не найден",
        )
    return slot


async def create_booking(
    db: AsyncSession,
    user_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> Booking:
    slot = await get_slot_or_404(db, slot_id)
    return await repo.create_booking(
        db,
        user_id=user_id,
        space_id=slot.space_id,
        slot_id=slot_id,
    )


async def get_user_bookings(
    db: AsyncSession, user_id: uuid.UUID
) -> list[BookingResponse]:
    return await repo.get_user_bookings(db, user_id)


async def cancel_booking(
    db: AsyncSession, booking_id: uuid.UUID, user_id: uuid.UUID
) -> Booking:
    return await repo.cancel_booking(db, booking_id, user_id)
