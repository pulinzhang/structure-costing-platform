"""操作日志按权限目录生成审计文案。"""

from types import SimpleNamespace

from app.common.operation_log.rules import (
    append_upload_filenames,
    describe_operation,
    format_audit_question,
    should_record,
)
from app.common.operation_log.upload_filename import collect_audit_upload_filenames
from app.common.permissions.catalog import (
    catalog_subtree_for_menu,
    get_audit_label,
    list_catalog_filter_options,
)
from app.common.permissions.codes import Perm


def test_stamping_parts_delete_uses_catalog_breadcrumb() -> None:
    meta = get_audit_label(Perm.STAMPING_PARTS_DELETE)
    assert meta is not None
    assert meta["op_label"] == "删除"
    assert meta["menu_label"] == "冲压零件列表"
    assert "冲压工程" in meta["breadcrumb"]
    assert "冲压零件列表" in meta["breadcrumb"]
    assert meta["breadcrumb"].endswith("删除")

    module, action, summary = describe_operation(
        "DELETE",
        "/api/stamping/parts/42",
        Perm.STAMPING_PARTS_DELETE,
    )
    assert module == "冲压零件列表"
    assert action == "删除"
    assert "冲压零件列表" in summary
    assert "/api/stamping/parts/42" in summary


def test_login_without_permission_code() -> None:
    module, action, summary = describe_operation("POST", "/api/auth/login", None)
    assert module == "登录认证"
    assert action == "登录"
    assert "登录" in summary


def test_grant_permissions_path_maps_catalog() -> None:
    module, action, summary = describe_operation(
        "PUT",
        "/api/settings/users/3/permissions",
        None,
    )
    assert module == "用户管理"
    assert action == "授权"
    assert "授权" in summary
    assert "user_id" not in summary


def test_assembly_cost_restore_get_is_recorded() -> None:
    assert should_record("GET", "/api/costing/assembly-costs/restore") is True
    assert should_record("GET", "/api/costing/assembly-costs/12/restore") is True
    assert should_record("GET", "/api/costing/assembly-costs") is False

    module, action, summary = describe_operation(
        "GET",
        "/api/costing/assembly-costs/restore",
        Perm.ASSEMBLY_COST_VIEW,
        query_string="year=2026&month=1&part_number=T13J-001&location=芜湖",
    )
    assert module == "总成核价一览"
    assert action == "查看计算过程"
    assert "查看计算过程" in summary
    assert "基地 芜湖" in summary
    assert "零件号 T13J-001" in summary
    assert "2026年01月" in summary
    assert "/api/costing/assembly-costs/restore" in summary
    assert not summary.endswith("查询")


def test_catalog_filter_options_include_menus_and_ops() -> None:
    menus, operations = list_catalog_filter_options()
    menu_codes = {item["code"] for item in menus}
    op_codes = {item["code"] for item in operations}
    assert Perm.MENU_ASSEMBLY_COST in menu_codes
    assert Perm.ASSEMBLY_COST_VIEW in op_codes
    view = next(item for item in operations if item["code"] == Perm.ASSEMBLY_COST_VIEW)
    assert view["parent_code"] == Perm.MENU_ASSEMBLY_COST
    assert "总成核价一览" in view["breadcrumb"]
    assert Perm.MENU_STAMPING in menu_codes


def test_catalog_subtree_includes_nested_ops() -> None:
    op_codes, labels = catalog_subtree_for_menu(Perm.MENU_STAMPING)
    assert Perm.STAMPING_PARTS_DELETE in op_codes
    assert "冲压零件列表" in labels
    assert "冲压工程" in labels


def test_collect_excel_filename_on_upload_path() -> None:
    items = [
        ("year", "2026"),
        ("file", SimpleNamespace(filename="C:\\\\docs\\\\冲压工艺.xlsx")),
    ]
    names = collect_audit_upload_filenames("/api/stamping/upload", items)
    assert names == ["冲压工艺.xlsx"]


def test_collect_skips_avatar_image() -> None:
    items = [("file", SimpleNamespace(filename="face.png"))]
    names = collect_audit_upload_filenames("/api/auth/avatar", items)
    assert names == []


def test_append_upload_filenames_in_summary() -> None:
    _, _, summary = describe_operation(
        "POST",
        "/api/stamping/upload",
        Perm.STAMPING_UPLOAD_UPLOAD,
    )
    decorated = append_upload_filenames(summary, ["模具布置.xlsx"])
    assert "文件 模具布置.xlsx" in decorated
    assert len(decorated) <= 255


def test_format_audit_question_compacts_whitespace() -> None:
    text = format_audit_question({"question": "  芜湖基地\n本月冲压件成本构成？  "})
    assert text == "芜湖基地 本月冲压件成本构成？"
