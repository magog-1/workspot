import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BookingCreate(BaseModel):
    slot_id: UUID


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    space_id: UUID
    slot_id: UUID
    status: str
    created_at: datetime.datetime

    # joined fields — populated manually in repository
    space_name: str = ""
    slot_date: datetime.date | None = None
    slot_time_from: datetime.time | None = None
    slot_time_to: datetime.time | None = None
