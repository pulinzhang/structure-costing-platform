"""FastAPI 入口：只编排应用工厂与生命周期。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap.exception_handlers import register_exception_handlers
from app.bootstrap.factory import build_fastapi
from app.bootstrap.frontend import register_frontend
from app.bootstrap.lifecycle import on_shutdown, on_startup
from app.bootstrap.middleware import register_middleware
from app.bootstrap.routers import include_scanned_routers
from app.config import settings
from app.utils.logging_config import LoggerConfig

LoggerConfig.configure()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    on_startup()
    yield
    on_shutdown()


def create_app() -> FastAPI:
    app = build_fastapi(lifespan=lifespan)
    register_middleware(app)
    register_exception_handlers(app)
    include_scanned_routers(app)
    register_frontend(app)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.IS_DEBUG,
        reload_dirs=["app"] if settings.IS_DEBUG else None,
        log_level="info",
        access_log=False,
    )
