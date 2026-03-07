import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class SpaceCreate(BaseModel):
    name: str
    address: str
    city: str = "Москва"
    description: str | None = None
    price_per_hour: float
    capacity: int
    amenities: list[str] = []
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("price_per_hour")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Цена должна быть больше нуля")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Вместимость должна быть больше нуля")
        return v


class SpaceUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    description: str | None = None
    price_per_hour: float | None = None
    capacity: int | None = None
    amenities: list[str] | None = None
    latitude: float | None = None
    longitude: float | None = None


class SlotGenerateRequest(BaseModel):
    date_from: datetime.date
    date_to: datetime.date

    @field_validator("date_to")
    @classmethod
    def date_to_gte_date_from(cls, v: datetime.date, info: Any) -> datetime.date:
        if "date_from" in info.data and v < info.data["date_from"]:
            raise ValueError("date_to должна быть не раньше date_from")
        return v
