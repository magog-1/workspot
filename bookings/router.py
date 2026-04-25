import uuid

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

import auth.service as auth_service
import bookings.service as bookings_service
from database import get_db

router = APIRouter(prefix="/bookings", tags=["bookings"])
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# POST /bookings  — создать бронирование
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_302_FOUND)
async def create_booking(
    request: Request,
    slot_id: uuid.UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    await bookings_service.create_booking(db, current_user.id, slot_id)
    return RedirectResponse(url="/bookings/my", status_code=status.HTTP_302_FOUND)


# ---------------------------------------------------------------------------
# GET /bookings/my  — список броней пользователя
# ---------------------------------------------------------------------------
@router.get("/my", response_class=HTMLResponse)
async def my_bookings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    bookings = await bookings_service.get_user_bookings(db, current_user.id)
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "bookings": bookings,
            "current_user": current_user,
            "msg": request.query_params.get("msg"),
        },
    )


# ---------------------------------------------------------------------------
# POST /bookings/{id}/cancel  — отмена (браузер не поддерживает DELETE)
# ---------------------------------------------------------------------------
@router.post("/{booking_id}/cancel", status_code=status.HTTP_302_FOUND)
async def cancel_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    await bookings_service.cancel_booking(db, booking_id, current_user.id)
    return RedirectResponse(url="/bookings/my", status_code=status.HTTP_302_FOUND)


# ---------------------------------------------------------------------------
# DELETE /bookings/{id}  — REST-вариант для Swagger / API-клиентов
# ---------------------------------------------------------------------------
@router.delete("/{booking_id}", status_code=status.HTTP_302_FOUND)
async def cancel_booking_delete(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user),
):
    await bookings_service.cancel_booking(db, booking_id, current_user.id)
    return RedirectResponse(url="/bookings/my", status_code=status.HTTP_302_FOUND)
