"""
FastAPI 应用入口
汽车冲压件自动核价平台

学习指南详见：docs/fastapi-guide.md
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings, ensure_directories
from app.utils.logging_config import LoggerConfig, log_request, log_response, get_logger
from app.database import DatabaseConfig


# 重要：在导入其他模块之前先配置日志，确保所有模块的 logger 都能正确获取日志器
# 这解决了模块导入顺序导致的日志器配置问题
logger = get_logger("main")
LoggerConfig.configure(force=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理，详见 docs/fastapi-guide.md 第8节"""
    # 启动时
    # 注意：日志配置应该在 uvicorn 启动前完成，这里只做保障
    from app.utils.logging_config import LoggerConfig
    LoggerConfig.configure(force=True)
    ensure_directories()
    DatabaseConfig.create_tables()

    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} 正在启动...")
    logger.info(f"版本: {settings.APP_VERSION}")
    logger.info(f"环境: {settings.ENV}")
    logger.info("=" * 50)
    logger.info("应用启动完成")
    logger.info(f"访问地址: http://{settings.HOST}:{settings.PORT}")

    yield  # 详见 docs/fastapi-guide.md 第8节

    # 关闭时
    logger.info("应用正在关闭...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例，详见 docs/fastapi-guide.md"""
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")
    # 把上传目录挂为静态资源，使 sketch_url 能直接通过 URL 访问
    app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

    # 创建模板引擎
    templates = Jinja2Templates(directory="templates")
    # 添加 settings 到模板全局上下文
    templates.env.globals["config"] = settings
    app.state.templates = templates

    # 详见 docs/fastapi-guide.md 第6节
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root(request: Request):
        """
        根路径重定向到 dashboard
        当用户访问 http://localhost:8000/ 时
        自动跳转到 /dashboard
        """
        # 注意：这里使用 from main import app 是为了获取模板引擎
        # 因为此时 app.state.templates 已经在 create_app() 中设置好了
        from main import app
        return app.state.templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "仪表盘",
            }
        )

    # 导入各个功能模块的路由
    from app.routers import dashboard, parts, costing, quotation, settings_router
    from app.routers.upload import stamping_router

    # include_router = 注册路由，详见 docs/fastapi-guide.md 第6节
    app.include_router(dashboard.router)
    app.include_router(stamping_router)
    app.include_router(parts.router)
    app.include_router(costing.router)
    app.include_router(quotation.router)
    app.include_router(settings_router.router)

    # 详见 docs/fastapi-guide.md 第7节
    @app.middleware("http")
    async def log_middleware(request: Request, call_next):
        """
        请求日志中间件
        每次请求都会先经过这里，记录日志后再继续处理
        """
        import time
        start_time = time.time()

        log_request(logger, request.method, request.url.path)

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, request.method, request.url.path, response.status_code, duration_ms)

        return response

    return app


# 创建应用实例
app = create_app()


# 程序入口
if __name__ == "__main__":
    import uvicorn

    # uvicorn.run() 内部是一个【无限循环】
    # 程序会一直运行，直到手动按 Ctrl+C 停止
    uvicorn.run(
        "main:app",  # "文件名:变量名" 的格式
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=False,  # 禁用 uvicorn 访问日志，使用我们自己的请求日志中间件
    )
