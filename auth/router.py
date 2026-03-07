from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

import auth.service as auth_service
from auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Cookie settings (shared)
# ---------------------------------------------------------------------------
_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=False)


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_302_FOUND)
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    data = RegisterRequest(email=email, password=password, name=name)
    await auth_service.register(db, data)

    tokens = await auth_service.login(
        db, LoginRequest(email=data.email, password=data.password)
    )

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie("access_token", tokens["access_token"], **_COOKIE_OPTS)
    response.set_cookie("refresh_token", tokens["refresh_token"], **_COOKIE_OPTS)
    return response


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", status_code=status.HTTP_302_FOUND)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    data = LoginRequest(email=email, password=password)
    tokens = await auth_service.login(db, data)

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie("access_token", tokens["access_token"], **_COOKIE_OPTS)
    response.set_cookie("refresh_token", tokens["refresh_token"], **_COOKIE_OPTS)
    return response


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request):
    new_access_token = await auth_service.refresh_access_token(request)

    response = JSONResponse(
        content={"access_token": new_access_token, "token_type": "bearer"}
    )
    response.set_cookie("access_token", new_access_token, **_COOKIE_OPTS)
    return response


# ---------------------------------------------------------------------------
# GET /auth/logout
# ---------------------------------------------------------------------------
@router.get("/logout", status_code=status.HTTP_302_FOUND)
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


# ---------------------------------------------------------------------------
# GET /auth/me  (вспомогательный JSON-эндпоинт для Swagger)
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def me(
    current_user=Depends(auth_service.get_current_user),
):
    return UserResponse.model_validate(current_user)
