"""操作日志：从上传表单提取可审计的文件名。"""

from __future__ import annotations

from collections.abc import Iterable

_EXCEL_SUFFIXES = (".xlsx", ".xls", ".xlsm", ".xlsb")
_MAX_FILENAME_LEN = 200


def sanitize_upload_filename(name: str) -> str:
    """去掉路径，只保留文件名。"""
    cleaned = name.replace("\\", "/").strip()
    return cleaned.rsplit("/", 1)[-1].strip()[:_MAX_FILENAME_LEN]


def is_excel_filename(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(_EXCEL_SUFFIXES)


def is_upload_path(path: str) -> bool:
    path_only = path.split("?", 1)[0].lower()
    return "upload" in path_only or "import" in path_only


def should_audit_upload_filename(path: str, filename: str) -> bool:
    """Excel 一律记；上传/导入接口上的其它文件名也记。"""
    if not filename:
        return False
    if is_excel_filename(filename):
        return True
    return is_upload_path(path)


def collect_audit_upload_filenames(
    path: str, form_items: Iterable[tuple[str, object]]
) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for _key, value in form_items:
        raw = getattr(value, "filename", None)
        if not isinstance(raw, str):
            continue
        name = sanitize_upload_filename(raw)
        if not name or name in seen:
            continue
        if not should_audit_upload_filename(path, name):
            continue
        seen.add(name)
        names.append(name)
    return names
