from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from admin.router import router as admin_router
from auth.router import router as auth_router
from bookings.router import router as bookings_router
from spaces.router import router as spaces_router
from users.router import router as users_router

app = FastAPI(
    title="WorkSpot",
    description="Платформа для поиска и бронирования коворкингов",
    version="1.0.0",
)

# Static files (uploaded photos, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates (shared instance, re-used in routers via dependency or direct import)
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(auth_router)
app.include_router(spaces_router)
app.include_router(bookings_router)
app.include_router(users_router)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/spaces")
