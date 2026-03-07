import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class BookingStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("slot_id", name="uq_booking_slot"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    space_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("timeslots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status = Column(
        Enum(BookingStatus, name="bookingstatus"),
        nullable=False,
        default=BookingStatus.active,
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    space = relationship("Space", foreign_keys=[space_id])
    slot = relationship("TimeSlot", foreign_keys=[slot_id])

    def __repr__(self) -> str:
        return f"<Booking id={self.id} user_id={self.user_id} status={self.status}>"
