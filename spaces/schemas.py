from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class SpaceFilter(BaseModel):
    city: str = "Москва"
    date: datetime.date | None = None
    price_max: float | None = None
    capacity: int | None = None
    amenities: list[str] | None = None


class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    city: str
    description: str | None
    price_per_hour: float
    capacity: int
    amenities: list[str]
    latitude: float | None
    longitude: float | None
    photos: list[str]

    @field_validator("price_per_hour", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> float:
        return float(v)

    def to_map_dict(self) -> dict:
        """Minimal dict for Yandex Maps JS payload."""
        return {
            "id": str(self.id),
            "name": self.name,
            "address": self.address,
            "price_per_hour": self.price_per_hour,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: datetime.date
    time_from: datetime.time
    time_to: datetime.time
    is_booked: bool


class SlotGenerateRequest(BaseModel):
    date_from: datetime.date
    date_to: datetime.date

    @field_validator("date_to")
    @classmethod
    def date_to_gte_date_from(cls, v: datetime.date, info: Any) -> datetime.date:
        if "date_from" in info.data and v < info.data["date_from"]:
            raise ValueError("date_to must be >= date_from")
        return v
