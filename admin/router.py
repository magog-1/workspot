import datetime
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import spaces.service as spaces_service
from admin.schemas import SpaceCreate, SpaceUpdate
from admin.service import require_admin
from auth.models import User
from bookings.models import Booking, BookingStatus
from database import get_db
from spaces.models import Space, TimeSlot

PAGE_SIZE = 20

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

_ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
_UPLOADS_DIR = os.path.join("static", "uploads")


# ---------------------------------------------------------------------------
# GET /admin/dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from spaces.schemas import SpaceFilter
    spaces = await spaces_service.get_all(db, SpaceFilter(city=""))
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "spaces": spaces,
            "current_user": current_user,
            "msg": request.query_params.get("msg"),
        },
    )


# ---------------------------------------------------------------------------
# POST /admin/spaces  — создать коворкинг
# ---------------------------------------------------------------------------
@router.post("/spaces", status_code=status.HTTP_302_FOUND)
async def create_space(
    request: Request,
    name: str = Form(...),
    address: str = Form(...),
    city: str = Form("Москва"),
    description: str | None = Form(None),
    price_per_hour: float = Form(...),
    capacity: int = Form(...),
    amenities: list[str] = Form(default=[]),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    data = SpaceCreate(
        name=name,
        address=address,
        city=city,
        description=description,
        price_per_hour=price_per_hour,
        capacity=capacity,
        amenities=amenities,
        latitude=latitude,
        longitude=longitude,
    )
    await spaces_service.create_space(db, **data.model_dump())
    return RedirectResponse(
        url="/admin/dashboard?msg=Коворкинг+создан",
        status_code=status.HTTP_302_FOUND,
    )


# ---------------------------------------------------------------------------
# POST /admin/spaces/{id}/edit  — обновить (браузер не поддерживает PATCH)
# ---------------------------------------------------------------------------
@router.post("/spaces/{space_id}/edit", status_code=status.HTTP_302_FOUND)
@router.patch("/spaces/{space_id}", status_code=status.HTTP_302_FOUND)
async def update_space(
    space_id: uuid.UUID,
    name: str | None = Form(None),
    address: str | None = Form(None),
    city: str | None = Form(None),
    description: str | None = Form(None),
    price_per_hour: float | None = Form(None),
    capacity: int | None = Form(None),
    amenities: list[str] | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    data = SpaceUpdate(
        name=name,
        address=address,
        city=city,
        description=description,
        price_per_hour=price_per_hour,
        capacity=capacity,
        amenities=amenities,
        latitude=latitude,
        longitude=longitude,
    )
    update_fields = data.model_dump(exclude_none=True)
    if update_fields:
        await spaces_service.update_space(db, space_id, **update_fields)
    return RedirectResponse(
        url="/admin/dashboard?msg=Коворкинг+обновлён",
        status_code=status.HTTP_302_FOUND,
    )


# ---------------------------------------------------------------------------
# POST /admin/spaces/{id}/delete  — удалить (браузер не поддерживает DELETE)
# ---------------------------------------------------------------------------
@router.post("/spaces/{space_id}/delete", status_code=status.HTTP_302_FOUND)
@router.delete("/spaces/{space_id}", status_code=status.HTTP_302_FOUND)
async def delete_space(
    space_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    await spaces_service.delete_space(db, space_id)
    return RedirectResponse(
        url="/admin/dashboard?msg=Коворкинг+удалён",
        status_code=status.HTTP_302_FOUND,
    )


# ---------------------------------------------------------------------------
# POST /admin/spaces/{id}/slots  — генерация слотов
# ---------------------------------------------------------------------------
@router.post("/spaces/{space_id}/slots", status_code=status.HTTP_302_FOUND)
async def generate_slots(
    space_id: uuid.UUID,
    date_from: datetime.date = Form(...),
    date_to: datetime.date = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    count = await spaces_service.generate_slots(db, space_id, date_from, date_to)
    return RedirectResponse(
        url=f"/admin/dashboard?msg=Создано+слотов:+{count}",
        status_code=status.HTTP_302_FOUND,
    )


# ---------------------------------------------------------------------------
# POST /admin/spaces/{id}/photo  — загрузка фото
# ---------------------------------------------------------------------------
@router.post("/spaces/{space_id}/photo", status_code=status.HTTP_302_FOUND)
async def upload_photo(
    space_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Validate extension
    original_name = file.filename or ""
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if ext not in _ALLOWED_PHOTO_EXTENSIONS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый формат файла. Разрешены: {', '.join(_ALLOWED_PHOTO_EXTENSIONS)}",
        )

    # Save file
    filename = f"{uuid.uuid4()}.{ext}"
    dest_path = os.path.join(_UPLOADS_DIR, filename)
    os.makedirs(_UPLOADS_DIR, exist_ok=True)

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Register path in DB (URL path, not filesystem path)
    photo_url = f"/static/uploads/{filename}"
    await spaces_service.add_photo(db, space_id, photo_url)

    return RedirectResponse(
        url="/admin/dashboard?msg=Фото+загружено",
        status_code=status.HTTP_302_FOUND,
    )


# ---------------------------------------------------------------------------
# GET /admin/bookings  — все брони клиентов
# ---------------------------------------------------------------------------
@router.get("/bookings", response_class=HTMLResponse)
async def admin_bookings(
    request: Request,
    status_filter: str | None = None,
    space_id: uuid.UUID | None = None,
    page: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from spaces.schemas import SpaceFilter

    # Build query with joins
    stmt = (
        select(
            Booking.id,
            Booking.status,
            Booking.created_at,
            User.name.label("user_name"),
            User.email.label("user_email"),
            Space.name.label("space_name"),
            Space.id.label("space_id"),
            TimeSlot.date.label("slot_date"),
            TimeSlot.time_from.label("slot_time_from"),
            TimeSlot.time_to.label("slot_time_to"),
        )
        .join(User, Booking.user_id == User.id)
        .join(Space, Booking.space_id == Space.id)
        .join(TimeSlot, Booking.slot_id == TimeSlot.id)
        .order_by(Booking.created_at.desc())
    )

    if status_filter in ("active", "cancelled"):
        stmt = stmt.where(Booking.status == status_filter)
    if space_id:
        stmt = stmt.where(Booking.space_id == space_id)

    total_stmt = select(Booking.id).join(User, Booking.user_id == User.id)
    if status_filter in ("active", "cancelled"):
        total_stmt = total_stmt.where(Booking.status == status_filter)
    if space_id:
        total_stmt = total_stmt.where(Booking.space_id == space_id)

    total_result = await db.execute(total_stmt)
    total = len(total_result.all())

    stmt = stmt.offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    result = await db.execute(stmt)
    rows = result.mappings().all()

    bookings = [
        {
            "id": str(row["id"]),
            "status": row["status"].value if hasattr(row["status"], "value") else row["status"],
            "created_at": row["created_at"],
            "user_name": row["user_name"],
            "user_email": row["user_email"],
            "space_name": row["space_name"],
            "space_id": str(row["space_id"]),
            "slot_date": row["slot_date"],
            "slot_time_from": row["slot_time_from"],
            "slot_time_to": row["slot_time_to"],
        }
        for row in rows
    ]

    spaces = await spaces_service.get_all(db, SpaceFilter(city=""))

    return templates.TemplateResponse(
        "admin/bookings.html",
        {
            "request": request,
            "bookings": bookings,
            "spaces": spaces,
            "current_user": current_user,
            "status_filter": status_filter or "",
            "space_id_filter": str(space_id) if space_id else "",
            "page": page,
            "total": total,
            "page_size": PAGE_SIZE,
            "has_prev": page > 0,
            "has_next": (page + 1) * PAGE_SIZE < total,
            "msg": request.query_params.get("msg"),
        },
    )


# ---------------------------------------------------------------------------
# POST /admin/bookings/{id}/cancel  — отмена брони администратором
# ---------------------------------------------------------------------------
@router.post("/bookings/{booking_id}/cancel", status_code=status.HTTP_302_FOUND)
async def admin_cancel_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from fastapi import HTTPException

    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")

    if booking.status != BookingStatus.cancelled:
        # Release slot
        await db.execute(
            update(TimeSlot)
            .where(TimeSlot.id == booking.slot_id)
            .values(is_booked=False)
            .execution_options(synchronize_session="fetch")
        )
        booking.status = BookingStatus.cancelled
        await db.flush()

    return RedirectResponse(
        url="/admin/bookings?msg=Бронирование+отменено",
        status_code=status.HTTP_302_FOUND,
    )
