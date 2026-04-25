from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from admin.router import router as admin_router
from auth.router import router as auth_router
from bookings.router import router as bookings_router
from observability.metrics import APIRequestMetricsMiddleware
from spaces.router import router as spaces_router
from users.router import profile_router
from users.router import router as users_router

app = FastAPI(
    title="WorkSpot",
    description="Платформа для поиска и бронирования коворкингов",
    version="1.0.0",
)

app.add_middleware(APIRequestMetricsMiddleware)

# Static files (uploaded photos, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates (shared instance, re-used in routers via dependency or direct import)
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(auth_router)
app.include_router(spaces_router)
app.include_router(bookings_router)
app.include_router(users_router)
app.include_router(profile_router)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/spaces")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
