import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: str
    created_at: datetime.datetime
