import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import Text as TextType

from database import Base


class Space(Base):
    __tablename__ = "spaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, default="Москва")
    description = Column(Text, nullable=True)
    price_per_hour = Column(Numeric(10, 2), nullable=False)
    capacity = Column(Integer, nullable=False)
    amenities = Column(ARRAY(TextType()), nullable=False, default=list)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    photos = Column(ARRAY(TextType()), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    slots = relationship(
        "TimeSlot",
        back_populates="space",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Space id={self.id} name={self.name}>"


class TimeSlot(Base):
    __tablename__ = "timeslots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False, index=True)
    time_from = Column(Time, nullable=False)
    time_to = Column(Time, nullable=False)
    is_booked = Column(Boolean, nullable=False, default=False)

    space = relationship("Space", back_populates="slots")

    def __repr__(self) -> str:
        return f"<TimeSlot id={self.id} space_id={self.space_id} date={self.date} {self.time_from}-{self.time_to}>"
