import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from spaces.models import Space


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> User | None:
    user = await get_by_id(db, user_id)
    if user is None:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(user, key, value)
    await db.flush()
    await db.refresh(user)
    return user
