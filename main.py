"""
FastAPI 应用入口
汽车冲压件自动核价平台

开发模式：前后端分离
- 后端：FastAPI API Server (端口 8000)
- 前端：静态 HTML + JavaScript (通过 Live Server 或 nginx)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, ensure_directories
from app.utils.logging_config import LoggerConfig, log_request, log_response, get_logger
from app.database import DatabaseConfig


# 重要：在导入其他模块之前先配置日志，确保所有模块的 logger 都能正确获取日志器
# 这解决了模块导入顺序导致的日志器配置问题
logger = get_logger("main")
LoggerConfig.configure(force=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    # 注意：日志配置应该在 uvicorn 启动前完成，这里只做保障
    from app.utils.logging_config import LoggerConfig
    LoggerConfig.configure(force=True)
    ensure_directories()
    # 导入所有模型，确保 Base.metadata 能扫描到表结构
    from app.models import StampingPart, StampingProcess, StampingTonnagePrice, SteelPrice, SteelPricePolicy, SteelPriceLadderItem
    # 自动迁移：在 create_tables 之前补充缺失的列
    from app.utils.db_migration import run_auto_migration
    run_auto_migration()
    # 钢材价格表业务主键变更迁移：在 create_tables 之前完成表重建
    from app.utils.steel_price_key_migration import run_steel_price_key_migration
    run_steel_price_key_migration(DatabaseConfig.get_engine())
    DatabaseConfig.create_tables()

    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} 正在启动...")
    logger.info(f"版本: {settings.APP_VERSION}")
    logger.info(f"环境: {settings.ENV}")
    logger.info("=" * 50)
    logger.info("API 服务启动完成")
    logger.info(f"API 访问地址: http://{settings.HOST}:{settings.PORT}")
    logger.info("前端静态页面: 使用 Live Server 打开 static/index.html")

    yield  # 详见 docs/fastapi-guide.md 第8节

    # 关闭时
    logger.info("应用正在关闭...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        debug=settings.DEBUG,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "docExpansion": "list",
            "tryItOutEnabled": True,
            "persistAuthorization": True,
            "filter": True,
            "displayRequestDuration": True,
            "operationsSorter": "method",  # 按 HTTP 方法排序：get > post > put > delete > patch
            "tagsSorter": "alpha",  # 按标签字母顺序排序
            "deepLinking": True,  # 支持 URL 锚点直接定位到接口
            "customSiteTitle": f"{settings.APP_NAME} - API 文档",
            "customCss": """
                /* ========== 基础布局 ========== */
                /* 隐藏顶部栏 */
                .swagger-ui .topbar { display: none; }
                /* 页面标题 */
                .swagger-ui .info .title {
                    color: #1e293b; font-weight: 700; font-size: 1.5em;
                    margin-bottom: 8px;
                }
                /* 页面描述 */
                .swagger-ui .info .description {
                    font-size: 14px; color: #64748b; margin-bottom: 20px;
                }

                /* ========== 侧边栏 ========== */
                /* 标签分组标题 */
                .swagger-ui .opblock-tag {
                    font-size: 13px; font-weight: 600; color: #334155;
                    border-bottom: 2px solid #e2e8f0;
                    padding-bottom: 8px; margin-bottom: 8px;
                }
                .swagger-ui .opblock-tag:hover { background-color: #f8fafc; }

                /* ========== 接口卡片 ========== */
                /* 展开/折叠 */
                .swagger-ui .opblock-summary-control { cursor: pointer; }
                /* GET 方法 - 绿色 */
                .swagger-ui .opblock.opblock-get .opblock-summary { border-left: 4px solid #16a34a; }
                .swagger-ui .opblock.opblock-get .opblock-summary-method {
                    background: #16a34a; color: white; font-weight: 600;
                }
                /* POST 方法 - 蓝色 */
                .swagger-ui .opblock.opblock-post .opblock-summary { border-left: 4px solid #2563eb; }
                .swagger-ui .opblock.opblock-post .opblock-summary-method {
                    background: #2563eb; color: white; font-weight: 600;
                }
                /* PUT 方法 - 橙色 */
                .swagger-ui .opblock.opblock-put .opblock-summary { border-left: 4px solid #d97706; }
                .swagger-ui .opblock.opblock-put .opblock-summary-method {
                    background: #d97706; color: white; font-weight: 600;
                }
                /* DELETE 方法 - 红色 */
                .swagger-ui .opblock.opblock-delete .opblock-summary { border-left: 4px solid #dc2626; }
                .swagger-ui .opblock.opblock-delete .opblock-summary-method {
                    background: #dc2626; color: white; font-weight: 600;
                }
                /* PATCH 方法 - 紫色 */
                .swagger-ui .opblock.opblock-patch .opblock-summary { border-left: 4px solid #9333ea; }
                .swagger-ui .opblock.opblock-patch .opblock-summary-method {
                    background: #9333ea; color: white; font-weight: 600;
                }

                /* ========== 按钮 ========== */
                /* Try it out 按钮 */
                .swagger-ui .btn.try-out__btn {
                    background-color: #0f172a; border-color: #0f172a; color: white;
                    font-weight: 500;
                }
                .swagger-ui .btn.try-out__btn:hover { background-color: #334155; }
                /* Execute 按钮 */
                .swagger-ui .btn.execute {
                    background-color: #2563eb; border-color: #2563eb;
                }
                .swagger-ui .btn.execute:hover { background-color: #1d4ed8; }
                /* Cancel 按钮 */
                .swagger-ui .btn.cancel {
                    background-color: #64748b; border-color: #64748b;
                }
                /* Authorize 按钮 */
                .swagger-ui .btn.authorize {
                    border-color: #2563eb; color: #2563eb;
                }
                .swagger-ui .btn.authorize:hover {
                    background-color: #2563eb; color: white;
                }

                /* ========== 输入框 ========== */
                .swagger-ui input:focus, .swagger-ui select:focus {
                    border-color: #2563eb;
                    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
                }
                /* 参数必填标记 */
                .swagger-ui .parameter__required { color: #dc2626; font-weight: 600; }

                /* ========== 响应区域 ========== */
                /* 成功响应 */
                .swagger-ui .response-col_status { color: #16a34a; font-weight: 600; }
                /* 错误响应 */
                .swagger-ui .response .tab-header { font-weight: 600; }

                /* ========== 状态码颜色 ========== */
                .swagger-ui .response-tabs input:checked + label {
                    color: #2563eb; border-color: #2563eb;
                }

                /* ========== 复制按钮 ========== */
                .swagger-ui .opblock-section-header .copy {
                    opacity: 0.5;
                }
                .swagger-ui .opblock-section-header .copy:hover {
                    opacity: 1;
                }

                /* ========== 搜索框 ========== */
                .swagger-ui .wrapper input {
                    border-radius: 6px; border: 1px solid #e2e8f0;
                }
            """,
        },
        openapi_tags=[
            {"name": "仪表盘", "description": "数据统计与看板"},
            {"name": "冲压工艺", "description": "冲压件零件与工序管理"},
            {"name": "冲压工艺上传", "description": "冲压工艺文件上传与解析"},
            {"name": "冲压吨位价格", "description": "冲压压机吨位单冲次价格管理"},
            {"name": "钢材价格管理", "description": "钢材价格文件导入与表格浏览"},
            {"name": "钢价政策管理", "description": "钢价政策主表与阶梯明细管理"},
            {"name": "零件", "description": "通用零件管理"},
            {"name": "核价", "description": "成本计算与核价"},
            {"name": "报价", "description": "报价单管理"},
            {"name": "系统设置", "description": "系统配置管理"},
        ]
    )

    # ========== CORS 配置 ==========
    # 根据环境配置 CORS（开发模式允许所有来源，生产环境使用白名单）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ========== 静态资源挂载 ==========
    app.mount("/static", StaticFiles(directory="static"), name="static")
    # 简图访问路径: http://host/uploads/T28/1.0/501008901AA.png
    app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

    # ========== 前端静态页面路由 ==========
    # SPA 入口页面（所有路由都指向 index.html）
    @app.get("/app", include_in_schema=False)
    async def spa_index():
        """单页应用入口"""
        from fastapi.responses import FileResponse
        return FileResponse("static/index.html")

    # favicon
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        from fastapi.responses import Response
        return Response(status_code=204)

    # 保留旧路由兼容性（重定向到 /app）
    @app.get("/", include_in_schema=False)
    async def root():
        """根路径重定向到 SPA"""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/app", status_code=302)

    # ========== 导入各个功能模块的路由 ==========
    from app.routers.dashboard.crud import router as dashboard_router
    from app.routers.costing.crud import router as costing_router
    from app.routers.quotation.crud import router as quotation_router
    from app.routers.settings.crud import router as settings_router
    from app.routers.stamping.crud import router as stamping_crud_router
    from app.routers.stamping.upload import router as stamping_upload_router
    from app.routers.stamping.tonnage_price import router as stamping_tonnage_price_router
    from app.routers.steel_price.crud import router as steel_price_router
    from app.routers.steel_price.steel_price_policy.crud import router as steel_price_policy_router

    # include_router = 注册路由
    app.include_router(dashboard_router)
    app.include_router(stamping_crud_router)
    app.include_router(stamping_upload_router)
    app.include_router(stamping_tonnage_price_router)
    app.include_router(steel_price_router)
    app.include_router(steel_price_policy_router)
    app.include_router(costing_router)
    app.include_router(quotation_router)
    app.include_router(settings_router)

    # ========== 请求日志中间件 ==========
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
