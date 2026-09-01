"""旧路径 307 到 /api/costing/assembly-costs。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

legacy_router = APIRouter(include_in_schema=False)


@legacy_router.api_route(
    "/api/costing/l0-assembly-costs",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def redirect_legacy_root(request: Request) -> RedirectResponse:
    target = "/api/costing/assembly-costs"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@legacy_router.api_route(
    "/api/costing/l0-assembly-costs/{rest:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def redirect_legacy_path(request: Request, rest: str) -> RedirectResponse:
    target = f"/api/costing/assembly-costs/{rest}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)
