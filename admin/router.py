import datetime
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

import spaces.service as spaces_service
from admin.schemas import SpaceCreate, SpaceUpdate
from admin.service import require_admin
from auth.models import User
from database import get_db

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
