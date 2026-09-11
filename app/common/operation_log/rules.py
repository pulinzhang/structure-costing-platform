"""操作日志：是否记录、模块/动作推断。"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote

from app.common.operation_log.context import OperationAuditScope
from app.common.permissions.catalog import get_audit_label
from app.common.permissions.codes import Perm

# 不记录：会话心跳、当前用户查询、退出（登录成功单独记录）
_SKIP_EXACT = {
    "/api/auth/touch",
    "/api/auth/me",
    "/api/auth/logout",
}

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _is_sensitive_query(path_only: str) -> bool:
    """特别重大的只读查询：打开即记审计（列表/心跳不记）。"""
    return path_only.rstrip("/").endswith("/restore")


_MODULE_RULES: list[tuple[str, str]] = [
    ("/api/settings/logs", "操作日志"),
    ("/api/stamping/process-fees", "冲压加工费"),
    ("/api/yishiyiyi/scrap-price", "废料月度销售价"),
    ("/api/stamping/tonnage-price", "冲次单价"),
    ("/api/bom/welding-unit-price", "焊接单价"),
    ("/api/bom/annual-part-price", "BOM年度零件价"),
    ("/api/bom/welding-process-breakdown", "焊接工艺拆解"),
    ("/api/bom/welding-fees", "焊接费"),
    ("/api/bom", "材料清单"),
    ("/api/stamping", "冲压工程"),
    ("/api/costing/steel-price/calc", "钢材联动计算"),
    ("/api/costing/steel-price", "钢材联动价格"),
    ("/api/costing/stamping-part-cost", "冲压零件价格核算"),
    ("/api/costing/engine", "核价引擎"),
    ("/api/yishiyiyi/policy", "加减价政策"),
    ("/api/yishiyiyi/base-price", "基准价格"),
    ("/api/yishiyiyi/winning-thickness", "中标钢厂厚度价格一览表"),
    ("/api/settings/users", "用户管理"),
    ("/api/settings/permissions", "权限管理"),
    ("/api/auth", "登录认证"),
    ("/api/settings/system", "系统设置"),
    ("/api/settings", "系统设置"),
    ("/api/dashboard", "仪表盘"),
    ("/api/costing", "核价"),
    ("/api/file-trace", "文件溯源"),
]


def should_record(method: str, path: str) -> bool:
    """写操作或文件导出需要记录；列表查询不记录。"""
    if not path.startswith("/api/"):
        return False
    path_only = path.split("?", 1)[0]
    if path_only in _SKIP_EXACT:
        return False
    # 操作日志列表本身不记（避免噪声）；导出走记录
    if (
        (path_only == "/api/settings/logs" or path_only.rstrip("/").endswith("/settings/logs"))
        and method == "GET"
        and "export" not in path_only
    ):
        return False
    method_upper = method.upper()
    if method_upper in _WRITE_METHODS:
        return True
    if method_upper == "GET":
        if _is_sensitive_query(path_only):
            return True
        # 仅真实导出文件；preview 视为查询
        if "export-preview" in path_only:
            return False
        if "export-download" in path_only or path_only.endswith("/export"):
            return True
        if "/download" in path_only:
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
    if (method_upper == "GET" or "export" in path_only) and (
        "export" in path_only or "download" in path_only
    ):
        return "export"
    if path_only.rstrip("/").endswith("/restore"):
        return "restore"
    if path_only.rstrip("/").endswith("/login"):
        return "login"
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


def describe_operation(
    method: str,
    path: str,
    permission_code: str | None,
    *,
    query_string: str = "",
    audit_scope: OperationAuditScope | None = None,
) -> tuple[str, str, str]:
    """返回 (module, action, summary)。优先用 catalog 面包屑，否则回退路径推断。"""
    path_only = path.split("?", 1)[0]
    sensitive = _describe_sensitive_query(
        method,
        path_only,
        query_string=query_string,
        audit_scope=audit_scope,
    )
    if sensitive is not None:
        return sensitive
    if permission_code:
        meta = get_audit_label(permission_code)
        if meta:
            summary = f"{meta['breadcrumb']} · {method.upper()} {path_only}"
            return meta["menu_label"], meta["op_label"], summary[:255]
    module = infer_module(path)
    action = infer_action(method, path)
    if path_only.rstrip("/") == "/api/auth/login":
        summary = f"登录认证 / 登录 · {method.upper()} {path_only}"
        return "登录认证", "登录", summary[:255]
    if path_only.rstrip("/").endswith("/permissions") and method.upper() in {"PUT", "POST"}:
        grant = get_audit_label(Perm.SETTINGS_USERS_GRANT)
        if grant:
            summary = f"{grant['breadcrumb']} · {method.upper()} {path_only}"
            return grant["menu_label"], grant["op_label"], summary[:255]
    return module, action, build_summary(method, path, action, module)


def _describe_sensitive_query(
    method: str,
    path_only: str,
    *,
    query_string: str,
    audit_scope: OperationAuditScope | None,
) -> tuple[str, str, str] | None:
    """重大只读查询用独立动作名，避免落成权限树上的「查询」。"""
    if not path_only.rstrip("/").endswith("/restore"):
        return None
    action = "查看计算过程"
    scope_text = format_restore_scope(audit_scope or _scope_from_query(query_string))
    suffix = f" · {scope_text}" if scope_text else ""
    meta = get_audit_label(Perm.ASSEMBLY_COST_VIEW)
    if meta:
        parent = meta["breadcrumb"].rsplit(" / ", 1)[0]
        summary = f"{parent} / {action}{suffix} · {method.upper()} {path_only}"
        return meta["menu_label"], action, summary[:255]
    return (
        "总成核价一览",
        action,
        f"总成核价一览 / {action}{suffix} · {method.upper()} {path_only}"[:255],
    )


def format_restore_scope(scope: OperationAuditScope) -> str:
    """基地 · 零件号 · 年度月份。"""
    parts: list[str] = []
    location = (scope.get("location") or "").strip()
    if location:
        parts.append(f"基地 {location}")
    part_number = (scope.get("part_number") or "").strip()
    if part_number:
        parts.append(f"零件号 {part_number}")
    year = (scope.get("year") or "").strip()
    month = (scope.get("month") or "").strip()
    if year or month:
        month_text = f"{int(month):02d}" if month.isdigit() else month
        if year and month_text:
            parts.append(f"{year}年{month_text}月")
        elif year:
            parts.append(f"{year}年")
        elif month_text:
            parts.append(f"{month_text}月")
    return " · ".join(parts)


def format_audit_question(scope: OperationAuditScope) -> str:
    """分析问题压成一行，供对象列展示。"""
    raw = (scope.get("question") or "").strip()
    if not raw:
        return ""
    compact = " ".join(raw.split())
    limit = 200
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "…"


def _scope_from_query(query_string: str) -> OperationAuditScope:
    if not query_string:
        return {}
    parsed = parse_qs(unquote(query_string), keep_blank_values=False)
    scope: OperationAuditScope = {}
    location_vals = parsed.get("location") or []
    if location_vals and location_vals[0].strip():
        scope["location"] = location_vals[0].strip()
    part_vals = parsed.get("part_number") or []
    if part_vals and part_vals[0].strip():
        scope["part_number"] = part_vals[0].strip()
    year_vals = parsed.get("year") or []
    if year_vals and year_vals[0].strip():
        scope["year"] = year_vals[0].strip()
    month_vals = parsed.get("month") or []
    if month_vals and month_vals[0].strip():
        scope["month"] = month_vals[0].strip()
    return scope


def build_summary(method: str, path: str, action: str, module: str) -> str:
    action_label = {
        "create": "新增",
        "login": "登录",
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
        "restore": "查看计算过程",
        "batch_delete": "批量删除",
        "batch_approve": "批量审核",
    }.get(action, action)
    path_only = path.split("?", 1)[0]
    return f"{module} · {action_label} · {method.upper()} {path_only}"


def append_upload_filenames(summary: str, upload_filenames: list[str] | None) -> str:
    """摘要末尾追加上传文件名，便于审计对照。"""
    if not upload_filenames:
        return summary[:255]
    file_text = "、".join(upload_filenames)
    return f"{summary} · 文件 {file_text}"[:255]
