"""FastAPI main application."""
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
import structlog
import sentry_sdk

from .config import settings
from .database import init_db, close_db
from .api.auth import router as auth_router
from .api.leads import router as leads_router
from .api.analytics import router as analytics_router
from .api.crm import router as crm_router
from .api.export import router as export_router
from .bot.handlers import router as bot_router
from .bot.middleware import RateLimitMiddleware, LoggingMiddleware
from .bot.mtproto_client import monitor

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0
    )

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True
)

logger = structlog.get_logger()


bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
dp.message.middleware(LoggingMiddleware())
dp.message.middleware(RateLimitMiddleware(limit=settings.RATE_LIMIT_PER_MINUTE))
dp.include_router(bot_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up", app=settings.APP_NAME)
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))

    monitor_started = False
    if settings.TELETHON_SESSION:
        try:
            await monitor.start()
            monitor_started = True
            logger.info("MTProto monitoring started")
        except Exception as e:
            logger.error("MTProto monitor failed to start — skipping group monitoring", error=str(e))
    else:
        logger.warning(
            "TELETHON_SESSION не задан — мониторинг групп выключен. "
            "Сгенерируй сессию: scripts/generate_session.py"
        )

    yield
    logger.info("Shutting down")
    dp.stop_polling()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    if monitor_started:
        await monitor.stop()
    await bot.session.close()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Real Estate Lead Collection Bot API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.MINI_APP_URL, "https://*.telegram.org"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(crm_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else None
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
