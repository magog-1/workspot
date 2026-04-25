import datetime
import json
import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

import auth.service as auth_service
import spaces.service as spaces_service
from config import settings
from database import get_db
from spaces.schemas import SlotResponse, SpaceFilter

router = APIRouter(prefix="/spaces", tags=["spaces"])
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# GET /spaces  — список коворкингов + Яндекс Карта
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("", response_class=HTMLResponse)
async def list_spaces(
    request: Request,
    city: str = Query("Москва"),
    date_: str | None = Query(None, alias="date"),
    price_max: str | None = Query(None),
    capacity: str | None = Query(None),
    amenities: list[str] | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user_optional),
):
    # Convert empty strings sent by the HTML form to None before validation
    def _date(v: str | None) -> datetime.date | None:
        if not v:
            return None
        try:
            return datetime.date.fromisoformat(v)
        except ValueError:
            return None

    def _float(v: str | None) -> float | None:
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def _int(v: str | None) -> int | None:
        if not v:
            return None
        try:
            return int(v)
        except ValueError:
            return None

    filters = SpaceFilter(
        city=city or "Москва",
        date=_date(date_),
        price_max=_float(price_max),
        capacity=_int(capacity),
        amenities=amenities or None,
    )

    spaces = await spaces_service.get_all(db, filters)
    spaces_map_data = spaces_service.spaces_to_map_json(spaces)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "spaces": spaces,
            "spaces_json": json.dumps(spaces_map_data, ensure_ascii=False),
            "filters": filters,
            "current_user": current_user,
            "yandex_api_key": settings.yandex_maps_api_key,
            "msg": request.query_params.get("msg"),
        },
    )


# ---------------------------------------------------------------------------
# GET /spaces/{id}  — детальная карточка
# ---------------------------------------------------------------------------
@router.get("/{space_id}", response_class=HTMLResponse)
async def space_detail(
    space_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(auth_service.get_current_user_optional),
):
    space = await spaces_service.get_space_or_404(db, space_id)
    return templates.TemplateResponse(
        "space_detail.html",
        {
            "request": request,
            "space": space,
            "current_user": current_user,
            "yandex_api_key": settings.yandex_maps_api_key,
            "msg": request.query_params.get("msg"),
        },
    )


# ---------------------------------------------------------------------------
# GET /spaces/{id}/slots  — доступные слоты по дате (JSON)
# ---------------------------------------------------------------------------
@router.get("/{space_id}/slots", response_model=list[SlotResponse])
async def get_slots(
    space_id: uuid.UUID,
    date_: datetime.date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
):
    slots = await spaces_service.get_slots(db, space_id, date_)
    return [SlotResponse.model_validate(s) for s in slots]
