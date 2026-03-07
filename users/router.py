from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

import auth.service as auth_service
import users.service as users_service
from database import get_db
from users.schemas import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# GET /users/me  — просмотр профиля
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(auth_service.get_current_user),
):
    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# PATCH /users/me  — редактирование профиля
# ---------------------------------------------------------------------------
@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    updated = await users_service.update_me(db, current_user, data)
    return UserResponse.model_validate(updated)
