"""操作日志：是否记录、模块/动作推断。"""

from __future__ import annotations

# 不记录：登录心跳、纯查询、静态与文档
_SKIP_EXACT = {
    "/api/auth/login",
    "/api/auth/touch",
    "/api/auth/me",
    "/api/auth/logout",
}

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_MODULE_RULES: list[tuple[str, str]] = [
    ("/api/operation-logs", "操作日志"),
    ("/api/stamping/scrap-prices", "废料月度销售价"),
    ("/api/stamping/tonnage-price", "冲次费率"),
    ("/api/stamping", "冲压工程"),
    ("/api/steel-prices/calc", "钢材联动计算"),
    ("/api/steel-prices", "钢材联动价格"),
    ("/api/steel-price-policies", "加减价政策"),
    ("/api/steel-base-prices", "基准价格"),
    ("/api/users", "用户管理"),
    ("/api/permissions", "权限管理"),
    ("/api/auth", "登录认证"),
    ("/api/settings", "系统设置"),
    ("/api/dashboard", "仪表盘"),
    ("/api/costing", "核价"),
    ("/api/quotation", "报价"),
]


def should_record(method: str, path: str) -> bool:
    """写操作或文件导出需要记录；列表查询不记录。"""
    if not path.startswith("/api/"):
        return False
    path_only = path.split("?", 1)[0]
    if path_only in _SKIP_EXACT:
        return False
    # 操作日志列表本身不记（避免噪声）；导出走记录
    if path_only == "/api/operation-logs" or path_only.rstrip("/").endswith(
        "/operation-logs"
    ):
        if method == "GET" and "export" not in path_only:
            return False
    method_upper = method.upper()
    if method_upper in _WRITE_METHODS:
        return True
    if method_upper == "GET":
        # 仅真实导出文件；preview 视为查询
        if "export-preview" in path_only:
            return False
        if "export-download" in path_only or path_only.endswith("/export"):
            return True
        if "/export" in path_only and "preview" not in path_only:
            return True
    return False


def infer_module(path: str) -> str:
    path_only = path.split("?", 1)[0]
    for prefix, label in _MODULE_RULES:
        if path_only.startswith(prefix):
            return label
    return "其它"


def infer_action(method: str, path: str) -> str:
    path_only = path.split("?", 1)[0]
    method_upper = method.upper()
    if method_upper == "GET" or "export" in path_only:
        if "export" in path_only or "download" in path_only:
            return "export"
    if "upload" in path_only or "import" in path_only:
        return "upload"
    if "password" in path_only:
        return "password"
    if "approve" in path_only:
        return "approve"
    if "reject" in path_only:
        return "reject"
    if "reverse" in path_only:
        return "reverse"
    if "permissions" in path_only and method_upper in {"PUT", "POST"}:
        return "grant"
    if "calc" in path_only and method_upper == "POST":
        return "run"
    if "batch" in path_only and method_upper == "DELETE":
        return "batch_delete"
    if "batch" in path_only and "approve" in path_only:
        return "batch_approve"
    mapping = {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }
    return mapping.get(method_upper, method_upper.lower())


def build_summary(method: str, path: str, action: str, module: str) -> str:
    action_label = {
        "create": "新增",
        "update": "修改",
        "delete": "删除",
        "export": "导出",
        "upload": "上传/导入",
        "password": "改密",
        "approve": "审核通过",
        "reject": "驳回",
        "reverse": "反审核",
        "grant": "授权",
        "run": "执行计算",
        "batch_delete": "批量删除",
        "batch_approve": "批量审核",
    }.get(action, action)
    path_only = path.split("?", 1)[0]
    return f"{module} · {action_label} · {method.upper()} {path_only}"
