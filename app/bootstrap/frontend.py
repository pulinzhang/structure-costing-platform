"""静态目录挂载与入口页（非业务 API）。"""

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, settings

_STATIC_DIR = BASE_DIR / "static"
# 容器健康检查只打这个地址。访问日志要跳过它，见 request_log 与 uvicorn.access 过滤。
HEALTH_PATH = "/health"
# 这些 HTML 的地址不变，里面写着带 ?v= 的脚本。必须每次核对，发版后才能拿到新版本号。
# 带 ?v= 的 /static/js、/static/css 不在这里改，见 app/middleware/frontend_cache.py。
_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}


def register_frontend(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

    @app.get("/app", include_in_schema=False)
    async def spa_index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html", headers=_NO_CACHE)

    @app.get("/login", include_in_schema=False)
    async def login_page() -> FileResponse:
        return FileResponse(_STATIC_DIR / "login.html", headers=_NO_CACHE)

    @app.get("/assembly-cost-calc-report", include_in_schema=False)
    async def assembly_cost_calc_report_page() -> FileResponse:
        return FileResponse(_STATIC_DIR / "assembly-cost-calc-report.html", headers=_NO_CACHE)

    @app.get("/assembly-cost-restore", include_in_schema=False)
    async def assembly_cost_restore_page() -> FileResponse:
        return FileResponse(_STATIC_DIR / "assembly-cost-restore.html", headers=_NO_CACHE)

    @app.get("/llm-analysis-report", include_in_schema=False)
    async def llm_analysis_report_page() -> FileResponse:
        return FileResponse(_STATIC_DIR / "llm-analysis-report.html", headers=_NO_CACHE)

    @app.get("/helper", include_in_schema=False)
    async def helper_redirect() -> RedirectResponse:
        return RedirectResponse(url="/helper/", status_code=302)

    app.mount(
        "/helper",
        StaticFiles(directory=str(_STATIC_DIR / "helper"), html=True),
        name="helper_site",
    )

    @app.get(HEALTH_PATH, include_in_schema=False)
    async def health() -> Response:
        return Response(content="ok", media_type="text/plain", status_code=200)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/login", status_code=302)
