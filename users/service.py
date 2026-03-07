import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import users.repository as repo
from auth.models import User
from users.schemas import UserUpdate


async def get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return user


async def update_me(db: AsyncSession, current_user: User, data: UserUpdate) -> User:
    if data.email and data.email != current_user.email:
        existing = await repo.get_by_email(db, data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует",
            )

    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        return current_user

    updated = await repo.update_user(db, current_user.id, **update_data)
    return updated
