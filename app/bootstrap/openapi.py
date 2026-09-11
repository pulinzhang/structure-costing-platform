"""OpenAPI / Swagger UI 展示参数。"""

from pathlib import Path
from typing import Any

from app.config import settings

_SWAGGER_CSS = (Path(__file__).resolve().parent / "swagger_ui.css").read_text(encoding="utf-8")

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "仪表盘", "description": "数据统计与看板"},
    {"name": "冲压工艺", "description": "冲压件零件与工序管理"},
    {"name": "冲压工艺上传", "description": "冲压工艺文件上传与解析"},
    {"name": "冲压冲次单价", "description": "冲压冲次单价管理"},
    {"name": "冲压加工费 API", "description": "冲压加工费计算与结果查询"},
    {"name": "钢材价格管理", "description": "钢材价格计算结果浏览、维护与审核"},
    {"name": "钢价政策管理", "description": "钢价政策主表与阶梯明细管理"},
    {"name": "钢材基准价格管理", "description": "钢材基准价格上传导出"},
    {"name": "核价", "description": "成本计算与核价"},
    {"name": "系统设置", "description": "系统配置管理"},
    {"name": "用户管理", "description": "用户账号增删改查"},
    {"name": "权限管理", "description": "权限目录与用户授权"},
    {"name": "操作日志", "description": "业务写操作与导出审计"},
    {"name": "登录认证", "description": "账号密码登录"},
]


def swagger_ui_parameters() -> dict[str, Any]:
    return {
        "defaultModelsExpandDepth": 1,
        "docExpansion": "list",
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "filter": True,
        "displayRequestDuration": True,
        "operationsSorter": "method",
        "tagsSorter": "alpha",
        "deepLinking": True,
        "customSiteTitle": f"{settings.APP_NAME} - API 文档",
        "customCss": _SWAGGER_CSS,
    }
