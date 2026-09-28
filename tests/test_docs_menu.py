"""文档左侧分组与现网侧栏一致。"""

from html.parser import HTMLParser
from pathlib import Path

from app.bootstrap.openapi import _MENU_GROUPS
from main import app

_SIDEBAR = Path(__file__).resolve().parents[1] / "static" / "index.html"
# 侧栏没有这两项，文档仍要能打开对应接口。
_EXTRA_SETTINGS_TAGS = ("登录认证",)
_EXTRA_GROUPS = (("AI助理", ("AI助理",)),)


class _SidebarMenuParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_sidebar = False
        self._anchor_class = ""
        self._capture = False
        self._span_taken = False
        self._buffer: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = _class_text(attrs)
        if tag == "aside" and "sidebar" in classes.split():
            self._in_sidebar = True
        if not self._in_sidebar:
            return
        if tag == "a":
            self._anchor_class = classes
            self._span_taken = False
        if tag == "span" and self._anchor_class and not self._span_taken:
            self._capture = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture:
            self.anchors.append((self._anchor_class, "".join(self._buffer).strip()))
            self._capture = False
            self._span_taken = True
        if tag == "a":
            self._anchor_class = ""
            self._span_taken = False
        if tag == "aside":
            self._in_sidebar = False

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)


def _class_text(attrs: list[tuple[str, str | None]]) -> str:
    for key, value in attrs:
        if key == "class" and value is not None:
            return value
    return ""


def _sidebar_groups() -> tuple[tuple[str, tuple[str, ...]], ...]:
    parser = _SidebarMenuParser()
    parser.feed(_SIDEBAR.read_text(encoding="utf-8"))
    groups: list[tuple[str, tuple[str, ...]]] = []
    current_name = ""
    current_children: list[str] = []
    for classes, text in parser.anchors:
        parts = classes.split()
        if "sidebar-nav-link" in parts:
            if current_name:
                groups.append((current_name, tuple(current_children or [current_name])))
            current_name = text
            current_children = []
        elif "submenu-link-nested" in parts:
            continue
        elif "submenu-link" in parts and current_name:
            current_children.append(text)
    if current_name:
        groups.append((current_name, tuple(current_children or [current_name])))
    return tuple(groups)


def _expected_groups() -> tuple[tuple[str, tuple[str, ...]], ...]:
    expected: list[tuple[str, tuple[str, ...]]] = []
    for name, children in _sidebar_groups():
        if name == "设置":
            expected.append((name, children + _EXTRA_SETTINGS_TAGS))
        else:
            expected.append((name, children))
    expected.extend(_EXTRA_GROUPS)
    return tuple(expected)


def test_docs_menu_matches_sidebar() -> None:
    assert _expected_groups() == _MENU_GROUPS


def test_openapi_sidebar_uses_menu_names() -> None:
    schema = app.openapi()
    raw_groups = schema.get("x-tagGroups")
    assert isinstance(raw_groups, list)
    groups = [(item["name"], tuple(item["tags"])) for item in raw_groups]
    assert groups[0] == ("仪表盘", ("仪表盘",))
    assert (
        "焊接工程",
        ("材料清单", "焊接单价", "包装运输费", "采购对象", "年度零件价", "焊接工艺拆解", "焊接费"),
    ) in groups
    assert (
        "冲压工程",
        ("冲压模具", "冲压工艺", "冲次单价", "冲压加工费", "冲压模具费", "冲压检具费"),
    ) in groups
    names = [name for name, _tags in groups]
    assert names.index("冲压工程") < names.index("焊接工程") < names.index("一事一议")
    assert names.index("核价") < names.index("采购价格协议") < names.index("文件溯源")
    assert "其他" not in names

    paths = schema["paths"]
    assert isinstance(paths, dict)
    auth = paths["/api/auth/me"]["get"]
    assert auth["tags"] == ["个人资料"]
    login = paths["/api/auth/login"]["post"]
    assert login["tags"] == ["登录认证"]
    bom = paths["/api/bom/upload"]["post"]
    assert bom["tags"] == ["材料清单"]
