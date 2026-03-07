import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User, UserRole


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    email: str,
    hashed_password: str,
    name: str,
    role: UserRole = UserRole.user,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        name=name,
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
