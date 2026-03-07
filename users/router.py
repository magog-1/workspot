from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

import auth.service as auth_service
import bookings.service as bookings_service
import users.service as users_service
from database import get_db
from users.schemas import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
profile_router = APIRouter(tags=["profile"])  # no prefix — serves /profile
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# GET /profile  — HTML страница профиля
# ---------------------------------------------------------------------------
@profile_router.get("/profile", response_class=HTMLResponse, include_in_schema=False)
async def profile_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    user_bookings = await bookings_service.get_user_bookings(db, current_user.id)
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "bookings": user_bookings,
            "active_tab": request.query_params.get("tab", "bookings"),
            "msg": request.query_params.get("msg"),
        },
    )


# ---------------------------------------------------------------------------
# GET /users/me  — просмотр профиля (JSON)
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(auth_service.get_current_user),
):
    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# PATCH /users/me  — редактирование профиля (JSON/REST)
# ---------------------------------------------------------------------------
@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    updated = await users_service.update_me(db, current_user, data)
    return UserResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# POST /users/me/name  — обновить имя (форма HTML)
# ---------------------------------------------------------------------------
@router.post("/me/name", include_in_schema=False)
async def update_name_form(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    await users_service.update_me(db, current_user, UserUpdate(name=name))
    return RedirectResponse(
        url="/profile?tab=account&msg=%D0%98%D0%BC%D1%8F+%D1%83%D1%81%D0%BF%D0%B5%D1%88%D0%BD%D0%BE+%D0%BE%D0%B1%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%BE",
        status_code=status.HTTP_302_FOUND,
    )

