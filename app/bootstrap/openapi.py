"""OpenAPI 文档页。Scalar 脚本与字体走本地，不请求外网。"""

import html
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings

_DOCS_CSS_PATH = Path(__file__).resolve().parent / "scalar_docs.css"

# 与 static/index.html 侧栏同序。元组是二级菜单名；没有二级时，文档项与一级同名。
# 登录认证、AI助理不在侧栏里，挂在菜单末尾，避免接口从文档消失。
_MENU_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("仪表盘", ("仪表盘",)),
    ("冲压工程", ("冲压模具", "冲压工艺", "冲次单价", "冲压加工费", "冲压模具费", "冲压检具费")),
    (
        "焊接工程",
        ("材料清单", "焊接单价", "包装运输费", "采购对象", "年度零件价", "焊接工艺拆解", "焊接费"),
    ),
    ("一事一议", ("加减价政策", "基准价格", "中标钢厂厚度价格列表", "废料月度销售价")),
    ("核价", ("冲压钢材联动价", "冲压零件价格核算", "总成核价", "自动核价引擎")),
    ("采购价格协议", ("采购价格协议",)),
    ("文件溯源", ("文件溯源",)),
    ("工程变更", ("设计变更", "材料变更")),
    ("主数据", ("基地", "项目", "供应商", "牌号分类")),
    ("设置", ("个人资料", "系统设置", "用户管理", "操作日志", "登录认证")),
    ("AI助理", ("AI助理",)),
)

_TAG_DESCRIPTION: dict[str, str] = {
    "仪表盘": "数据统计与看板",
    "冲压模具": "模具布点、模具列表与模具单价",
    "冲压工艺": "工艺文件与冲压零件",
    "冲次单价": "冲次单价上传与列表",
    "冲压加工费": "冲压加工费计算与列表",
    "冲压模具费": "冲压模具费计算与列表",
    "冲压检具费": "检具费上传与列表",
    "材料清单": "材料清单、产品结构与零件用在哪",
    "焊接单价": "焊接单价上传与列表",
    "包装运输费": "包装运输费上传与列表",
    "采购对象": "采购对象生成、列表与供应商",
    "年度零件价": "年度零件价上传与列表",
    "焊接工艺拆解": "焊接工艺拆解与拆解列表",
    "焊接费": "焊接费计算与列表",
    "加减价政策": "加减价政策上传与列表",
    "基准价格": "基准价格上传与列表",
    "中标钢厂厚度价格列表": "中标钢厂厚度价格",
    "冲压钢材联动价": "冲压钢材联动计算与列表",
    "冲压零件价格核算": "冲压零件价格计算与列表",
    "总成核价": "总成核价计算、列表与月度核对",
    "文件溯源": "上传文件溯源",
    "设计变更": "设计变更上传与列表",
    "材料变更": "材料变更上传与列表",
    "项目": "项目上传与列表",
    "供应商": "供应商上传与列表",
    "个人资料": "当前账号资料、头像与密码",
    "系统设置": "系统配置",
    "用户管理": "用户账号与权限",
    "操作日志": "业务写操作与导出审计",
    "登录认证": "登录、退出与会话心跳",
    "AI助理": "采购助理对话与分析报告",
}

# 路由上的旧标签 → 侧栏上的菜单名。同一菜单下的上传/列表/计算收成一项。
_ROUTER_TAG_TO_MENU: dict[str, str] = {
    "仪表盘 API": "仪表盘",
    "冲压模具 API": "冲压模具",
    "冲压模具单价": "冲压模具",
    "冲压工艺 API": "冲压工艺",
    "冲压工艺上传 API": "冲压工艺",
    "冲次单价 API": "冲次单价",
    "冲压加工费 API": "冲压加工费",
    "冲压模具费 API": "冲压模具费",
    "BOM API": "材料清单",
    "BOM 零件用在哪": "材料清单",
    "焊接单价 API": "焊接单价",
    "BOM 包装运输费 API": "包装运输费",
    "BOM 采购对象列表 API": "采购对象",
    "BOM 年度零件价 API": "年度零件价",
    "BOM 焊接工艺拆解 API": "焊接工艺拆解",
    "BOM 焊接费 API": "焊接费",
    "钢价政策上传": "加减价政策",
    "钢价政策管理": "加减价政策",
    "钢价政策导出": "加减价政策",
    "钢材基准价格": "基准价格",
    "废料月度销售价格": "废料月度销售价",
    "钢材价格计算": "冲压钢材联动价",
    "钢材价格管理": "冲压钢材联动价",
    "冲压零件价格计算": "冲压零件价格核算",
    "总成核价计算": "总成核价",
    "月度核对导出": "总成核价",
    "核价引擎 API": "自动核价引擎",
    "工程变更": "设计变更",
    "系统设置 API": "系统设置",
    "权限管理": "用户管理",
}

_PROFILE_PATHS = frozenset({"/api/auth/me", "/api/auth/avatar", "/api/auth/password"})
_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})


def _tag_entry(name: str) -> dict[str, str]:
    description = _TAG_DESCRIPTION.get(name, "")
    if not description:
        return {"name": name}
    return {"name": name, "description": description}


OPENAPI_TAGS: list[dict[str, str]] = [
    _tag_entry(name) for _group, names in _MENU_GROUPS for name in names
]

_SCALAR_JS_URL = "/static/js/vendor/scalar/api-reference.js"
_FONTS_CSS_URL = "/static/css/fonts.css"
_FAVICON_URL = "/static/assets/favicon.ico"


def _root_path(request: Request) -> str:
    raw_root = request.scope.get("root_path", "")
    if not isinstance(raw_root, str):
        return ""
    return raw_root.rstrip("/")


def _configuration_json(openapi_url: str) -> str:
    payload = {
        "url": openapi_url,
        "theme": "none",
        "layout": "modern",
        "darkMode": False,
        "forceDarkModeState": "light",
        "hideDarkModeToggle": True,
        "withDefaultFonts": False,
        "telemetry": False,
        "persistAuth": True,
        "documentDownloadType": "both",
        "searchHotKey": "k",
        "defaultOpenFirstTag": False,
        "orderRequiredPropertiesFirst": True,
        "operationsSorter": "method",
        "favicon": _FAVICON_URL,
        "defaultHttpClient": {"targetKey": "shell", "clientKey": "curl"},
        "localization": {"locale": "zh-CN"},
        "agent": {"disabled": True},
        "metaData": {
            "title": f"{settings.APP_NAME} API",
            "description": settings.APP_DESCRIPTION,
        },
    }
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")


def _scalar_page(*, openapi_url: str, title: str) -> str:
    safe_title = html.escape(title)
    safe_description = html.escape(settings.APP_DESCRIPTION)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="light" />
    <meta name="description" content="{safe_description}" />
    <title>{safe_title}</title>
    <link rel="icon" href="{_FAVICON_URL}" />
    <link rel="stylesheet" href="{_FONTS_CSS_URL}" />
  </head>
  <body>
    <div id="app"></div>
    <script src="{_SCALAR_JS_URL}"></script>
    <script>
      Scalar.createApiReference("#app", {_configuration_json(openapi_url)});
      const openSectionTitles = new Set();
      function sectionHeading(target) {{
        if (!(target instanceof Element)) return null;
        const heading = target.closest("div.font-sidebar");
        if (!(heading instanceof HTMLElement)) return null;
        const list = heading.nextElementSibling;
        if (!list || list.tagName !== "UL") return null;
        return heading;
      }}
      function syncSidebarSections() {{
        document.querySelectorAll("div.font-sidebar").forEach((heading) => {{
          if (!(heading instanceof HTMLElement) || !sectionHeading(heading)) return;
          const title = (heading.textContent || "").trim();
          const open = openSectionTitles.has(title);
          heading.classList.toggle("is-collapsed", !open);
          heading.setAttribute("role", "button");
          heading.tabIndex = 0;
          heading.setAttribute("aria-expanded", open ? "true" : "false");
        }});
      }}
      function toggleSidebarSection(heading) {{
        const title = (heading.textContent || "").trim();
        const open = heading.classList.contains("is-collapsed");
        heading.classList.toggle("is-collapsed", !open);
        heading.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) openSectionTitles.add(title);
        else openSectionTitles.delete(title);
      }}
      document.addEventListener("click", (event) => {{
        const heading = sectionHeading(event.target);
        if (!heading) return;
        event.preventDefault();
        event.stopPropagation();
        toggleSidebarSection(heading);
      }}, true);
      document.addEventListener("keydown", (event) => {{
        if (event.key !== "Enter" && event.key !== " ") return;
        const heading = sectionHeading(event.target);
        if (!heading) return;
        event.preventDefault();
        event.stopPropagation();
        toggleSidebarSection(heading);
      }}, true);
      const docsRoot = document.getElementById("app");
      if (docsRoot) {{
        syncSidebarSections();
        new MutationObserver(syncSidebarSections).observe(docsRoot, {{
          childList: true,
          subtree: true,
        }});
      }}
    </script>
    <!-- 样式放在 Scalar 注入之后，菜单悬停和选中才能压过组件类。 -->
    <style>
{_DOCS_CSS_PATH.read_text(encoding="utf-8")}
    </style>
  </body>
</html>
"""


def _menu_tag(path: str, tag: str) -> str:
    if path.startswith("/api/auth/") or path == "/api/auth":
        if path in _PROFILE_PATHS:
            return "个人资料"
        return "登录认证"
    return _ROUTER_TAG_TO_MENU.get(tag, tag)


def _align_docs_menu(schema: dict[str, object]) -> None:
    """把接口标签收成与侧栏一致的分组，供 Scalar 左侧菜单使用。"""
    paths = schema.get("paths")
    used: list[str] = []
    seen: set[str] = set()
    if isinstance(paths, dict):
        for path, item in paths.items():
            if not isinstance(path, str) or not isinstance(item, dict):
                continue
            for method, operation in item.items():
                if method not in _HTTP_METHODS or not isinstance(operation, dict):
                    continue
                raw_tags = operation.get("tags")
                if not isinstance(raw_tags, list):
                    continue
                menu_tags: list[str] = []
                for raw in raw_tags:
                    if not isinstance(raw, str):
                        continue
                    name = _menu_tag(path, raw)
                    if name not in menu_tags:
                        menu_tags.append(name)
                    if name not in seen:
                        seen.add(name)
                        used.append(name)
                operation["tags"] = menu_tags

    groups: list[tuple[str, list[str]]] = []
    placed: set[str] = set()
    for group_name, names in _MENU_GROUPS:
        present = [name for name in names if name in seen]
        placed.update(present)
        if present:
            groups.append((group_name, present))
    extra = [name for name in used if name not in placed]
    if extra:
        groups.append(("其他", extra))

    tag_entries: list[dict[str, str]] = []
    tag_groups: list[dict[str, object]] = []
    for group_name, menu_names in groups:
        tag_groups.append({"name": group_name, "tags": menu_names})
        for name in menu_names:
            tag_entries.append(_tag_entry(name))
    schema["tags"] = tag_entries
    schema["x-tagGroups"] = tag_groups


def _bind_docs_menu(app: FastAPI) -> None:
    generate_schema = app.openapi
    aligned = False

    def openapi() -> dict[str, object]:
        nonlocal aligned
        schema = generate_schema()
        if not aligned:
            _align_docs_menu(schema)
            aligned = True
        return schema

    # FastAPI 把 openapi 定义成方法；文档分组必须在生成 schema 之后改，只能换这个入口。
    app.openapi = openapi  # type: ignore[method-assign]


def register_local_docs(app: FastAPI) -> None:
    """用本地 Scalar 挂上文档页。/redoc 转到 /docs。"""
    _bind_docs_menu(app)
    openapi_url = app.openapi_url
    if not isinstance(openapi_url, str) or not openapi_url:
        return

    @app.get("/docs", include_in_schema=False)
    async def scalar_html(request: Request) -> HTMLResponse:
        page = _scalar_page(
            openapi_url=f"{_root_path(request)}{openapi_url}",
            title=f"{settings.APP_NAME} API",
        )
        return HTMLResponse(page)

    @app.get("/redoc", include_in_schema=False)
    async def redoc_redirect(request: Request) -> RedirectResponse:
        return RedirectResponse(url=f"{_root_path(request)}/docs", status_code=307)
