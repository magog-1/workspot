import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bookings.models import Booking, BookingStatus
from bookings.schemas import BookingResponse
from observability.metrics import (
    BOOKING_COLLISIONS_TOTAL,
    BOOKING_CREATE_ATTEMPTS_TOTAL,
    BOOKING_CREATE_SUCCESS_TOTAL,
)
from spaces.models import Space, TimeSlot

# ---------------------------------------------------------------------------
# Create booking — atomic double-booking prevention
# ---------------------------------------------------------------------------


async def create_booking(
    db: AsyncSession,
    user_id: uuid.UUID,
    space_id: uuid.UUID,
    slot_id: uuid.UUID,
) -> Booking:
    BOOKING_CREATE_ATTEMPTS_TOTAL.inc()

    # Step 1: Atomically mark slot as booked only if still free
    stmt = (
        update(TimeSlot)
        .where(
            and_(
                TimeSlot.id == slot_id,
                TimeSlot.is_booked == False,  # noqa: E712
            )
        )
        .values(is_booked=True)
        .execution_options(synchronize_session="fetch")
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        BOOKING_COLLISIONS_TOTAL.inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Слот уже занят",
        )

    # Step 2: Create booking record
    booking = Booking(
        id=uuid.uuid4(),
        user_id=user_id,
        space_id=space_id,
        slot_id=slot_id,
        status=BookingStatus.active,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    BOOKING_CREATE_SUCCESS_TOTAL.inc()
    return booking


# ---------------------------------------------------------------------------
# Get user bookings — joined with Space and TimeSlot
# ---------------------------------------------------------------------------


async def get_user_bookings(db: AsyncSession, user_id: uuid.UUID) -> list[BookingResponse]:
    result = await db.execute(
        select(
            Booking,
            Space.name.label("space_name"),
            TimeSlot.date.label("slot_date"),
            TimeSlot.time_from.label("slot_time_from"),
            TimeSlot.time_to.label("slot_time_to"),
        )
        .join(Space, Booking.space_id == Space.id)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )

    rows = result.all()
    bookings: list[BookingResponse] = []
    for row in rows:
        b: Booking = row[0]
        resp = BookingResponse(
            id=b.id,
            space_id=b.space_id,
            slot_id=b.slot_id,
            status=b.status.value if hasattr(b.status, "value") else str(b.status),
            created_at=b.created_at,
            space_name=row.space_name,
            slot_date=row.slot_date,
            slot_time_from=row.slot_time_from,
            slot_time_to=row.slot_time_to,
        )
        bookings.append(resp)
    return bookings


# ---------------------------------------------------------------------------
# Cancel booking
# ---------------------------------------------------------------------------


async def cancel_booking(db: AsyncSession, booking_id: uuid.UUID, user_id: uuid.UUID) -> Booking:
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бронирование не найдено",
        )
    if booking.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому бронированию",
        )
    if booking.status == BookingStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бронирование уже отменено",
        )

    # Release slot
    await db.execute(
        update(TimeSlot)
        .where(TimeSlot.id == booking.slot_id)
        .values(is_booked=False)
        .execution_options(synchronize_session="fetch")
    )

    booking.status = BookingStatus.cancelled
    await db.flush()
    await db.refresh(booking)
    return booking
