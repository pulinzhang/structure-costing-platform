"""创建 FastAPI 实例（不含中间件、路由、静态页）。"""

from fastapi import Depends, FastAPI
from starlette.types import Lifespan

from app.bootstrap.openapi import OPENAPI_TAGS, register_local_docs
from app.config import settings
from app.deps.operation_log_upload import capture_upload_filenames


def build_fastapi(*, lifespan: Lifespan[FastAPI]) -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        debug=settings.IS_DEBUG,
        dependencies=[Depends(capture_upload_filenames)],
        docs_url=None,
        redoc_url=None,
        openapi_tags=OPENAPI_TAGS,
    )
    register_local_docs(app)
    return app
