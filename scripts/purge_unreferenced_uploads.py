"""
清理 uploads 里现网业务不再引用的文件。

保留依据是业务表上的路径和来源文件名，不是 upload_files 登记。
工程变更的落盘路径只写在 upload_files.stored_relpath，脚本只解析
仍被单据或上传日志外键指着的那几行，不把溯源表当成保留清单。

同一归档目录里，来源文件名仍出现在业务行上时，只留该文件名最新的一份。
业务表不存这份上传的文件名时（窄表、采购对象供应商），范围内还有数据就留该目录最新一份。

默认只统计。--apply 把多余文件挪到 data/purged-uploads/{时间}/，并写 manifest.txt。
不改数据库。

用法（仓库根目录）::

    python -X utf8 -m scripts.purge_unreferenced_uploads
    python -X utf8 -m scripts.purge_unreferenced_uploads --apply
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.common.timezone import now
from app.config import BASE_DIR, settings

logger = logging.getLogger("scripts.purge_unreferenced_uploads")

PROTECTED_NAMES = frozenset({".gitkeep", "README.md"})
SPREADSHEET_SUFFIXES = frozenset({".xlsx", ".xls", ".xlsm", ".csv"})
RESERVED_TOP = frozenset({"bom", "steel-price", "stamping", "avatars"})
SPECIAL_VEHICLE_DIRS = frozenset(
    {"die", "gauge_fee", "engineering_change", "engineering_change_material"}
)
_UNSAFE_SEGMENT = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
KIND_MARKERS = (
    "base-price",
    "policy",
    "packaging-transport-fee",
    "welding-unit-price",
    "annual-part-price",
    "tonnage-price",
    "procurement-object-supplier",
)


@dataclass
class DiskFile:
    relpath: str
    size: int
    mtime: float
    name: str


@dataclass
class ArchiveHit:
    relpath: str
    size: int
    mtime: float
    name: str
    rule: str
    scope: tuple[str, ...]
    original_names: tuple[str, ...]


@dataclass
class References:
    exact_paths: set[str] = field(default_factory=set)
    steel_base_names: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    steel_policy_names: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    packaging_names: dict[tuple[str, str, str], set[str]] = field(default_factory=dict)
    welding_scopes: set[tuple[str, str]] = field(default_factory=set)
    annual_scopes: set[tuple[str, str]] = field(default_factory=set)
    tonnage_scopes: set[tuple[str, str]] = field(default_factory=set)
    procurement_scopes: set[tuple[str, str, str]] = field(default_factory=set)
    die_names: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    gauge_scopes: set[tuple[str, str]] = field(default_factory=set)
    stamping_names: dict[tuple[str, str, str], set[str]] = field(default_factory=dict)


def sqlite_file(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise SystemExit(f"只支持 sqlite 数据库: {url}")
    return Path(url[len(prefix) :])


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def normalize_relpath(value: object, upload_root: Path) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    unified = text.replace("\\", "/")
    if unified.startswith("/uploads/"):
        unified = unified[len("/uploads/") :]
    elif unified.startswith("uploads/"):
        unified = unified[len("uploads/") :]
    candidate = Path(text)
    if candidate.is_absolute():
        try:
            relative = candidate.resolve().relative_to(upload_root.resolve())
        except ValueError:
            return None
        unified = relative.as_posix()
    unified = unified.lstrip("/")
    if not unified or ".." in Path(unified).parts:
        return None
    return unified


def archive_segment(value: str) -> str:
    """与采购对象供应商归档目录同一套段名清洗。"""
    text = value.strip() or "unknown"
    text = _UNSAFE_SEGMENT.sub("_", text)
    text = text.replace(" ", "_").rstrip(". ")
    return text or "unknown"


def filename_of(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    name = Path(value.replace("\\", "/")).name.strip()
    return name or None


def add_name(
    bucket: dict[tuple[str, ...], set[str]], key: tuple[str, ...], name: str | None
) -> None:
    if not name:
        return
    bucket.setdefault(key, set()).add(name)


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def load_exact_paths(connection: sqlite3.Connection, upload_root: Path) -> set[str]:
    found: set[str] = set()
    queries = (
        "SELECT source_file_path FROM bom_snapshots",
        "SELECT sketch_url FROM bom_nodes",
        "SELECT sketch_url FROM stamping_parts",
        "SELECT sketch_url FROM stamping_process_fees",
        "SELECT sketch_url FROM stamping_part_costs",
        "SELECT sketch_url FROM costing_assembly_costs",
        "SELECT avatar FROM users",
    )
    for sql in queries:
        for row in connection.execute(sql):
            relpath = normalize_relpath(row[0], upload_root)
            if relpath:
                found.add(relpath)
    if table_exists(connection, "user_tokens"):
        for row in connection.execute("SELECT avatar FROM user_tokens"):
            relpath = normalize_relpath(row[0], upload_root)
            if relpath:
                found.add(relpath)

    if table_exists(connection, "upload_files"):
        id_sql = """
            SELECT stored_relpath
            FROM upload_files
            WHERE id IN (
                SELECT upload_file_id FROM engineering_change_orders
                UNION
                SELECT upload_file_id FROM engineering_change_upload_logs
                UNION
                SELECT upload_file_id FROM engineering_change_material_orders
                UNION
                SELECT upload_file_id FROM engineering_change_material_upload_logs
            )
        """
        for row in connection.execute(id_sql):
            relpath = normalize_relpath(row[0], upload_root)
            if relpath:
                found.add(relpath)
    return found


def load_references(connection: sqlite3.Connection, upload_root: Path) -> References:
    refs = References(exact_paths=load_exact_paths(connection, upload_root))

    for row in connection.execute("SELECT year, month, excel_filename FROM steel_base_prices"):
        add_name(refs.steel_base_names, (str(row[0]), f"{int(row[1]):02d}"), filename_of(row[2]))
    for row in connection.execute("SELECT year, month, base_excel_filename FROM steel_prices"):
        add_name(refs.steel_base_names, (str(row[0]), f"{int(row[1]):02d}"), filename_of(row[2]))

    for row in connection.execute("SELECT year, month, excel_filename FROM steel_price_policies"):
        add_name(refs.steel_policy_names, (str(row[0]), f"{int(row[1]):02d}"), filename_of(row[2]))
    for row in connection.execute(
        """
        SELECT year, month, thickness_excel_filename, width_excel_filename, zinc_excel_filename
        FROM steel_prices
        """
    ):
        key = (str(row[0]), f"{int(row[1]):02d}")
        add_name(refs.steel_policy_names, key, filename_of(row[2]))
        add_name(refs.steel_policy_names, key, filename_of(row[3]))
        add_name(refs.steel_policy_names, key, filename_of(row[4]))

    for row in connection.execute(
        """
        SELECT year, location, vehicle_model, excel_filename
        FROM bom_packaging_transport_fees
        """
    ):
        key = (str(row[0]), str(row[1]), str(row[2]))
        add_name(refs.packaging_names, key, filename_of(row[3]))

    for row in connection.execute("SELECT year, location FROM bom_welding_unit_price"):
        refs.welding_scopes.add((str(row[0]), str(row[1])))
    for row in connection.execute("SELECT year, location FROM bom_annual_part_prices"):
        refs.annual_scopes.add((str(row[0]), str(row[1])))
    for row in connection.execute("SELECT year, location FROM stamping_tonnage_price"):
        refs.tonnage_scopes.add((str(row[0]), str(row[1])))

    for row in connection.execute(
        "SELECT location, vehicle_model, bom_version FROM bom_procurement_object_lists"
    ):
        refs.procurement_scopes.add(
            (
                archive_segment(str(row[0])),
                archive_segment(str(row[1])),
                archive_segment(str(row[2])),
            )
        )

    for row in connection.execute(
        "SELECT location, vehicle_model, excel_filename FROM stamping_die_parts"
    ):
        add_name(refs.die_names, (str(row[0]), str(row[1])), filename_of(row[2]))
    for row in connection.execute(
        "SELECT location, vehicle_model, excel_filename FROM stamping_die_fees"
    ):
        add_name(refs.die_names, (str(row[0]), str(row[1])), filename_of(row[2]))

    for row in connection.execute("SELECT location, vehicle_model FROM stamping_gauge_fees"):
        refs.gauge_scopes.add((str(row[0]), str(row[1])))

    for sql in (
        "SELECT location, vehicle_model, version, excel_filename FROM stamping_parts",
        "SELECT location, vehicle_model, version, excel_filename FROM stamping_process_fees",
        "SELECT location, vehicle_model, version, excel_filename FROM stamping_part_costs",
    ):
        for row in connection.execute(sql):
            add_name(
                refs.stamping_names,
                (str(row[0]), str(row[1]), str(row[2])),
                filename_of(row[3]),
            )
    return refs


def load_trace_status(connection: sqlite3.Connection) -> dict[str, str]:
    """诊断用：相对路径 → active/superseded。不参与保留判断。"""
    if not table_exists(connection, "upload_files"):
        return {}
    found: dict[str, str] = {}
    for row in connection.execute("SELECT stored_relpath, status FROM upload_files"):
        relpath = str(row[0]).replace("\\", "/").lstrip("/")
        found[relpath] = str(row[1])
    return found


def list_disk_files(upload_root: Path) -> list[DiskFile]:
    files: list[DiskFile] = []
    for path in upload_root.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        files.append(
            DiskFile(
                relpath=path.relative_to(upload_root).as_posix(),
                size=stat.st_size,
                mtime=stat.st_mtime,
                name=path.name,
            )
        )
    return files


def original_candidates(remainder: str) -> tuple[str, ...]:
    names = [remainder]
    head, separator, tail = remainder.partition("_")
    if separator and head.isdigit() and Path(tail).suffix:
        names.append(tail)
    return tuple(dict.fromkeys(names))


def parse_kind_name(filename: str) -> tuple[str, tuple[str, ...]] | None:
    """{YYYYMMDD}_{HHMMSS}_{kind}_{原名} → (kind, 候选原名)。"""
    parts = filename.split("_", 3)
    if len(parts) < 4:
        return None
    if not (
        len(parts[0]) == 8 and parts[0].isdigit() and len(parts[1]) == 6 and parts[1].isdigit()
    ):
        return None
    kind = parts[2]
    if kind not in KIND_MARKERS:
        return None
    if not parts[3]:
        return None
    return kind, original_candidates(parts[3])


def parse_dated_original(filename: str) -> tuple[str, ...] | None:
    """{YYYYMMDD}_{HHMMSS}_{原名}，模具布点用。"""
    date_text, first_sep, rest = filename.partition("_")
    if not first_sep or len(date_text) != 8 or not date_text.isdigit():
        return None
    clock, second_sep, original = rest.partition("_")
    if not second_sep or len(clock) != 6 or not clock.isdigit() or not original:
        return None
    return original_candidates(original)


def parse_stamping_original(
    filename: str, location: str, vehicle_model: str, version: str
) -> tuple[str, ...] | None:
    prefix = f"{location}_{vehicle_model}_{version}_"
    if not filename.startswith(prefix):
        return None
    rest = filename[len(prefix) :]
    if len(rest) < 8 or not rest[:6].isdigit() or rest[6] != "_":
        return None
    original = rest[7:]
    if not original:
        return None
    return (original,)


def classify(disk_file: DiskFile) -> ArchiveHit | None:
    if disk_file.name in PROTECTED_NAMES:
        return None
    if Path(disk_file.name).suffix.lower() not in SPREADSHEET_SUFFIXES:
        return None
    parts = disk_file.relpath.split("/")
    parsed = parse_kind_name(disk_file.name)
    if len(parts) == 4 and parts[0] == "steel-price" and parts[1].isdigit() and parts[2].isdigit():
        if parsed is None or parsed[0] not in {"base-price", "policy"}:
            return None
        month = f"{int(parts[2]):02d}"
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="steel-" + parsed[0],
            scope=(parts[1], month),
            original_names=parsed[1],
        )
    if (
        len(parts) == 6
        and parts[0] == "bom"
        and parts[1] == "packaging-transport-fee"
        and parts[2].isdigit()
        and parsed is not None
        and parsed[0] == "packaging-transport-fee"
    ):
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="packaging",
            scope=(parts[2], parts[3], parts[4]),
            original_names=parsed[1],
        )
    if (
        len(parts) == 5
        and parts[0] == "bom"
        and parts[1] == "welding-unit-price"
        and parts[2].isdigit()
        and parsed is not None
        and parsed[0] == "welding-unit-price"
    ):
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="welding",
            scope=(parts[2], parts[3]),
            original_names=parsed[1],
        )
    if (
        len(parts) == 5
        and parts[0] == "bom"
        and parts[1] == "annual-part-price"
        and parts[2].isdigit()
        and parsed is not None
        and parsed[0] == "annual-part-price"
    ):
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="annual",
            scope=(parts[2], parts[3]),
            original_names=parsed[1],
        )
    if (
        len(parts) == 6
        and parts[0] == "bom"
        and parts[1] == "procurement-object-supplier"
        and parsed is not None
        and parsed[0] == "procurement-object-supplier"
    ):
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="procurement",
            scope=(parts[2], parts[3], parts[4]),
            original_names=parsed[1],
        )
    if (
        len(parts) == 5
        and parts[0] == "stamping"
        and parts[1] == "tonnage-price"
        and parts[2].isdigit()
        and parsed is not None
        and parsed[0] == "tonnage-price"
    ):
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="tonnage",
            scope=(parts[2], parts[3]),
            original_names=parsed[1],
        )
    if len(parts) == 4 and parts[0] not in RESERVED_TOP and parts[2] == "die":
        originals = parse_dated_original(disk_file.name) or (disk_file.name,)
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="die",
            scope=(parts[0], parts[1]),
            original_names=originals,
        )
    if len(parts) == 4 and parts[0] not in RESERVED_TOP and parts[2] == "gauge_fee":
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="gauge",
            scope=(parts[0], parts[1]),
            original_names=(),
        )
    if len(parts) == 4 and parts[0] not in RESERVED_TOP and parts[2] not in SPECIAL_VEHICLE_DIRS:
        originals = parse_stamping_original(disk_file.name, parts[0], parts[1], parts[2])
        if originals is None:
            return None
        return ArchiveHit(
            relpath=disk_file.relpath,
            size=disk_file.size,
            mtime=disk_file.mtime,
            name=disk_file.name,
            rule="stamping",
            scope=(parts[0], parts[1], parts[2]),
            original_names=originals,
        )
    return None


def newest(items: list[ArchiveHit]) -> ArchiveHit:
    return max(items, key=lambda item: (item.mtime, item.name))


def pick_named(items: list[ArchiveHit], names: set[str]) -> tuple[list[ArchiveHit], str]:
    grouped: dict[str, list[ArchiveHit]] = defaultdict(list)
    for item in items:
        for candidate in item.original_names:
            if candidate in names:
                grouped[candidate].append(item)
                break
    if grouped:
        return [newest(group) for group in grouped.values()], "filename"
    if names:
        return [newest(items)], "fallback"
    return [], "none"


def pick_scope(items: list[ArchiveHit], active: bool) -> tuple[list[ArchiveHit], str]:
    if active and items:
        return [newest(items)], "scope"
    return [], "none"


def choose_hits(items: list[ArchiveHit], refs: References) -> tuple[list[ArchiveHit], str]:
    rule = items[0].rule
    scope = items[0].scope
    if rule == "steel-base-price":
        return pick_named(items, refs.steel_base_names.get((scope[0], scope[1]), set()))
    if rule == "steel-policy":
        return pick_named(items, refs.steel_policy_names.get((scope[0], scope[1]), set()))
    if rule == "packaging":
        return pick_named(items, refs.packaging_names.get((scope[0], scope[1], scope[2]), set()))
    if rule == "procurement":
        return pick_scope(items, (scope[0], scope[1], scope[2]) in refs.procurement_scopes)
    if rule == "die":
        return pick_named(items, refs.die_names.get((scope[0], scope[1]), set()))
    if rule == "stamping":
        return pick_named(items, refs.stamping_names.get((scope[0], scope[1], scope[2]), set()))
    if rule == "welding":
        return pick_scope(items, scope in refs.welding_scopes)
    if rule == "annual":
        return pick_scope(items, scope in refs.annual_scopes)
    if rule == "tonnage":
        return pick_scope(items, scope in refs.tonnage_scopes)
    if rule == "gauge":
        return pick_scope(items, scope in refs.gauge_scopes)
    return [], "none"


def plan(files: list[DiskFile], refs: References) -> dict[str, str]:
    """相对路径 → 保留原因。不在字典里的文件会被清掉。"""
    reasons: dict[str, str] = {}
    on_disk = {item.relpath for item in files}
    for item in files:
        if item.name in PROTECTED_NAMES:
            reasons[item.relpath] = "protected"
    for relpath in refs.exact_paths:
        if relpath in on_disk and relpath not in reasons:
            reasons[relpath] = "exact-path"

    groups: dict[tuple[str, tuple[str, ...]], list[ArchiveHit]] = defaultdict(list)
    for item in files:
        hit = classify(item)
        if hit is not None:
            groups[(hit.rule, hit.scope)].append(hit)
    for grouped in groups.values():
        chosen, how = choose_hits(grouped, refs)
        if how == "none":
            continue
        label = f"{grouped[0].rule}:{how}"
        for hit in chosen:
            reasons.setdefault(hit.relpath, label)
    return reasons


def remove_empty_dirs(upload_root: Path) -> int:
    removed = 0
    for dirpath, _dirnames, _filenames in os.walk(upload_root, topdown=False):
        path = Path(dirpath)
        if path == upload_root:
            continue
        if any(path.iterdir()):
            continue
        path.rmdir()
        removed += 1
    return removed


def apply_moves(upload_root: Path, removals: list[DiskFile], archive_root: Path) -> Path:
    stamp = now().strftime("%Y%m%d_%H%M%S")
    destination_root = archive_root / stamp
    destination_root.mkdir(parents=True, exist_ok=False)
    manifest = destination_root / "manifest.txt"
    lines = ["relpath\tsize"]
    for item in removals:
        source = upload_root / item.relpath
        target = destination_root / item.relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise SystemExit(f"归档目标已存在: {target}")
        shutil.move(str(source), str(target))
        lines.append(f"{item.relpath}\t{item.size}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emptied = remove_empty_dirs(upload_root)
    logger.info("已挪走 %d 个文件，清空空目录 %d 个", len(removals), emptied)
    logger.info("归档目录: %s", destination_root)
    return destination_root


def report(
    files: list[DiskFile],
    reasons: dict[str, str],
    trace_status: dict[str, str],
) -> list[DiskFile]:
    removals = [item for item in files if item.relpath not in reasons]
    kept = Counter(reasons.values())
    removed_bytes = sum(item.size for item in removals)
    logger.info(
        "磁盘 %d 个文件，保留 %d，待清理 %d（%.1f MB）",
        len(files),
        len(reasons),
        len(removals),
        removed_bytes / 1024 / 1024,
    )
    for label, count in sorted(kept.items()):
        logger.info("  保留 %-24s %d", label, count)
    by_top = Counter(item.relpath.split("/", 1)[0] for item in removals)
    for name, count in by_top.most_common():
        logger.info("  清理 %-24s %d", name, count)

    active_hit = [item.relpath for item in removals if trace_status.get(item.relpath) == "active"]
    superseded_hit = [
        item.relpath for item in removals if trace_status.get(item.relpath) == "superseded"
    ]
    logger.info(
        "诊断（不参与取舍）: 待清理里溯源 active=%d superseded=%d 未登记=%d",
        len(active_hit),
        len(superseded_hit),
        len(removals) - len(active_hit) - len(superseded_hit),
    )
    for relpath in active_hit[:30]:
        logger.info("  active 仍将被清掉: %s", relpath)
    if len(active_hit) > 30:
        logger.info("  ... 另有 %d 条 active", len(active_hit) - 30)
    return removals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按现网业务引用清理 uploads 多余文件")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="把多余文件挪到 data/purged-uploads/。省略时只统计",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    upload_root = settings.UPLOAD_DIR.resolve()
    if not upload_root.is_dir():
        logger.error("上传目录不存在: %s", upload_root)
        return 1
    db_path = sqlite_file(settings.DATABASE_URL)
    connection = connect_readonly(db_path)
    try:
        refs = load_references(connection, upload_root)
        trace_status = load_trace_status(connection)
        aux_path = sqlite_file(settings.AUXILIARY_DATABASE_URL)
        if aux_path.is_file():
            aux = connect_readonly(aux_path)
            try:
                if table_exists(aux, "user_tokens"):
                    for row in aux.execute("SELECT avatar FROM user_tokens"):
                        relpath = normalize_relpath(row[0], upload_root)
                        if relpath:
                            refs.exact_paths.add(relpath)
            finally:
                aux.close()
    finally:
        connection.close()

    files = list_disk_files(upload_root)
    reasons = plan(files, refs)
    removals = report(files, reasons, trace_status)
    if not args.apply:
        logger.info("未加 --apply，文件仍在原处")
        return 0
    if not removals:
        logger.info("没有可清理的文件")
        return 0
    archive_root = BASE_DIR / "data" / "purged-uploads"
    apply_moves(upload_root, removals, archive_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
