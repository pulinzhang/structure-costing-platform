"""
FastAPI 应用入口
汽车冲压件自动核价平台

开发模式：前后端分离
- 后端：FastAPI API Server (端口 8000)
- 前端：静态 HTML + JavaScript (通过 Live Server 或 nginx)
"""

from contextlib import asynccontextmanager
import socket

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging_config import LoggerConfig, log_request, log_response, get_logger


# 重要：在导入其他模块之前先配置日志，确保所有模块的 logger 都能正确获取日志器
# 这解决了模块导入顺序导致的日志器配置问题
logger = get_logger("main")
LoggerConfig.configure(force=True)


def _local_ipv4_addresses() -> list[str]:
    """本机非回环 IPv4，供启动日志打印局域网访问地址。"""
    addresses: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if ip.startswith("127.") or ip in addresses:
                continue
            addresses.append(ip)
    except OSError:
        pass
    if not addresses:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip = sock.getsockname()[0]
                if not ip.startswith("127."):
                    addresses.append(ip)
        except OSError:
            pass
    return addresses


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    # 注意：日志配置应该在 uvicorn 启动前完成，这里只做保障
    from app.utils.logging_config import LoggerConfig
    LoggerConfig.configure(force=True)

    # 教学/开发交付：空库用 create_all 建表即可，不做历史库 Schema 升级
    from app.config import ensure_directories
    from app.database import AuxiliaryDatabaseConfig, DatabaseConfig

    ensure_directories()
    from app import models as _orm_models  # noqa: F401  # 执行 models/__init__，注册全部 ORM 表
    DatabaseConfig.create_tables()
    AuxiliaryDatabaseConfig.create_tables()

    from app.services.settings.users.user_service import UserService

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        UserService().ensure_default_admin(db)
    finally:
        db.close()

    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} 正在启动...")
    logger.info(f"版本: {settings.APP_VERSION}")
    logger.info(f"环境: {settings.ENV}")
    logger.info("=" * 50)
    logger.info("API 服务启动完成")
    # 监听仍是 settings.HOST（常为 0.0.0.0）；日志打印可点开的本机与局域网地址
    display_host = "127.0.0.1" if settings.HOST in {"0.0.0.0", "::"} else settings.HOST
    logger.info(f"本机访问: http://{display_host}:{settings.PORT}")
    if settings.HOST in {"0.0.0.0", "::"}:
        for lan_ip in _local_ipv4_addresses():
            logger.info(f"局域网访问: http://{lan_ip}:{settings.PORT}")
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
        debug=settings.IS_DEBUG,
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
            {"name": "冲压冲次单价", "description": "冲压冲次单价管理"},
            {"name": "冲压加工费 API", "description": "冲压加工费计算与结果查询"},
            {"name": "钢材价格管理", "description": "钢材价格计算结果浏览、维护与审核"},
            {"name": "钢价政策管理", "description": "钢价政策主表与阶梯明细管理"},
            {"name": "钢材基准价格管理", "description": "钢材基准价格上传导出"},
            {"name": "零件", "description": "通用零件管理"},
            {"name": "核价", "description": "成本计算与核价"},
            {"name": "报价", "description": "报价单管理"},
            {"name": "系统设置", "description": "系统配置管理"},
            {"name": "用户管理", "description": "用户账号增删改查"},
            {"name": "权限管理", "description": "权限目录与用户授权"},
            {"name": "操作日志", "description": "业务写操作与导出审计"},
            {"name": "登录认证", "description": "账号密码登录"},
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

    # 操作审计：写操作 + 导出（须在 CORS 之后添加，以便作为外层拿到最终响应）
    from app.middleware.operation_log_middleware import OperationLogMiddleware
    from app.middleware.no_cache_frontend import NoCacheFrontendMiddleware

    app.add_middleware(OperationLogMiddleware)
    # 前端 JS/CSS/入口页禁止强缓存，避免修复后仍命中旧坏脚本
    app.add_middleware(NoCacheFrontendMiddleware)

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
        return FileResponse(
            "static/index.html",
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )

    # 登录页（账号密码入口，登录成功后再进主系统）
    @app.get("/login", include_in_schema=False)
    async def login_page():
        """打开登录页面"""
        from fastapi.responses import FileResponse
        return FileResponse(
            "static/login.html",
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )

    # 使用帮助站（独立静态目录：index / help / knowledge / example + css/img）
    # /helper → /helper/ ；子页用相对路径，如 help.html、helper.css、img/...
    @app.get("/helper", include_in_schema=False)
    async def helper_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/helper/", status_code=302)

    app.mount(
        "/helper",
        StaticFiles(directory="static/helper", html=True),
        name="helper_site",
    )

    # favicon
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        from fastapi.responses import Response
        return Response(status_code=204)

    # 保留旧路由兼容性（未登录先进鉴权页）
    @app.get("/", include_in_schema=False)
    async def root():
        """根路径重定向到独立登录页"""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)

    # ========== 导入各个功能模块的路由 ==========
    from app.routers.dashboard.crud import router as dashboard_router
    from app.routers.bom.crud import router as bom_router
    from app.routers.bom.upload import router as bom_upload_router
    from app.routers.bom.welding_unit_price import router as bom_welding_unit_price_router
    from app.routers.bom.annual_part_price import (
        router as bom_annual_part_price_router,
    )
    from app.routers.bom.packaging_transport_fee import (
        router as bom_packaging_transport_fee_router,
    )
    from app.routers.bom.welding_process_breakdown import (
        router as bom_welding_process_breakdown_router,
    )
    from app.routers.bom.l0_welding_fee import router as bom_l0_welding_fee_router
    from app.routers.costing.engine.crud import router as costing_engine_router
    from app.routers.file_trace.crud import router as file_trace_router
    from app.routers.settings.system.crud import router as settings_router
    from app.routers.stamping.crud import router as stamping_crud_router
    from app.routers.stamping.upload import router as stamping_upload_router
    from app.routers.stamping.tonnage_price import router as stamping_tonnage_price_router
    from app.routers.stamping.stamping_process_fee import router as stamping_process_fee_router
    from app.routers.costing.stamping_part_cost.calc import (
        router as costing_stamping_part_cost_calc_router,
    )
    from app.routers.costing.stamping_part_cost.crud import (
        router as costing_stamping_part_cost_router,
    )
    from app.routers.costing.l0_assembly_cost.calc import (
        router as costing_l0_assembly_cost_calc_router,
    )
    from app.routers.costing.l0_assembly_cost.crud import (
        router as costing_l0_assembly_cost_router,
    )
    from app.routers.costing.monthly_bundle_export.crud import (
        router as costing_monthly_bundle_export_router,
    )
    from app.routers.costing.steel_price.crud import router as costing_steel_price_router
    from app.routers.costing.steel_price.calc import router as costing_steel_price_calc_router
    from app.routers.yishiyiyi.policy.upload import router as yishiyiyi_policy_upload_router
    from app.routers.yishiyiyi.policy.export import router as yishiyiyi_policy_export_router
    from app.routers.yishiyiyi.policy.crud import router as yishiyiyi_policy_router
    from app.routers.yishiyiyi.base_price.crud import router as yishiyiyi_base_price_router
    from app.routers.yishiyiyi.winning_thickness.crud import router as yishiyiyi_winning_thickness_router
    from app.routers.yishiyiyi.scrap_price.crud import router as yishiyiyi_scrap_price_router
    from app.routers.settings.auth.crud import router as auth_router
    from app.routers.settings.users.crud import router as user_crud_router
    from app.routers.settings.users.permissions import router as permissions_router
    from app.routers.settings.logs.crud import router as operation_log_router
    from app.routers.llm.reports import router as llm_reports_router

    # include_router = 注册路由（鉴权由各端点 Depends(get_current_user) 声明）
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(stamping_crud_router)
    app.include_router(stamping_upload_router)
    app.include_router(stamping_tonnage_price_router)
    app.include_router(stamping_process_fee_router)
    app.include_router(costing_stamping_part_cost_calc_router)
    app.include_router(costing_stamping_part_cost_router)
    app.include_router(costing_l0_assembly_cost_calc_router)
    app.include_router(costing_l0_assembly_cost_router)
    app.include_router(costing_monthly_bundle_export_router)
    app.include_router(costing_steel_price_calc_router)
    app.include_router(costing_steel_price_router)
    app.include_router(yishiyiyi_policy_upload_router)
    app.include_router(yishiyiyi_policy_export_router)
    app.include_router(yishiyiyi_policy_router)
    app.include_router(yishiyiyi_base_price_router)
    app.include_router(yishiyiyi_winning_thickness_router)
    app.include_router(yishiyiyi_scrap_price_router)
    app.include_router(bom_router)
    app.include_router(bom_upload_router)
    app.include_router(bom_welding_unit_price_router)
    app.include_router(bom_annual_part_price_router)
    app.include_router(bom_packaging_transport_fee_router)
    app.include_router(bom_welding_process_breakdown_router)
    app.include_router(bom_l0_welding_fee_router)
    app.include_router(costing_engine_router)
    app.include_router(file_trace_router)
    app.include_router(settings_router)
    app.include_router(user_crud_router)
    app.include_router(permissions_router)
    app.include_router(operation_log_router)
    app.include_router(llm_reports_router)

    # ========== 全局异常处理器 ==========
    from app.exceptions.handlers import (
        http_exception_handler,
        validation_exception_handler,
        business_exception_handler,
        generic_exception_handler,
    )
    from app.exceptions.base import BusinessException
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

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
    # reload 默认监视整个项目目录；logs/、data/ 等运行时文件一写盘就会刷
    # "N change detected"。只监视业务代码目录，避免日志/SQLite 触发误报。
    uvicorn.run(
        "main:app",  # "文件名:变量名" 的格式
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.IS_DEBUG,
        reload_dirs=["app"] if settings.IS_DEBUG else None,
        log_level="info",
        access_log=False,  # 禁用 uvicorn 访问日志，使用我们自己的请求日志中间件
    )
