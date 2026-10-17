import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import TexoraException
from app.api import auth, users, messages, chats, groups, notifications, uploads, moderation, admin
from app.websocket import events
from app.modules.moderation.queue import moderation_queue

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("texora")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Texora...")
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    moderation_queue.start()
    yield
    logger.info("Shutting down Texora...")
    await moderation_queue.stop()


app = FastAPI(
    title=settings.APP_NAME,
    description="پلتفرم پیام‌رسان فارسی با نظارت هوشمند",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TexoraException)
async def texora_exception_handler(request: Request, exc: TexoraException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "خطای داخلی سرور"})


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(groups.router)
app.include_router(messages.router)
app.include_router(uploads.router)
app.include_router(notifications.router)
app.include_router(moderation.router)
app.include_router(admin.router)
app.include_router(events.router)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
async def index(request: Request):
    # ✅ روش جدید (سازگار با starlette جدید)
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")


@app.get("/admin")
async def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}