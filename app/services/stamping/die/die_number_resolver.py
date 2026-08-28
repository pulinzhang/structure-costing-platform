"""模具布点对照冲压工艺：零件号、工序、有尺寸时的模具编号。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class DieLayoutCheckRow:
    part_number: str
    process_seq: str
    has_die_size: bool


@dataclass(frozen=True, slots=True)
class StampingProcessTrace:
    part_number: str
    process_seq: str
    die_number: str | None
    excel_filename: str
    stamping_supplier: str | None
    version: str | None = None


@dataclass(frozen=True, slots=True)
class DieLayoutSource:
    excel_filename: str
    stamping_supplier: str | None = None
    die_number: str | None = None
    version: str | None = None


@dataclass(frozen=True, slots=True)
class DieLayoutIssue:
    kind: Literal["part_missing", "process_missing", "die_number_missing", "die_number_conflict"]
    part_number: str
    process_seq: str
    values: tuple[str, ...] = ()
    sources: tuple[DieLayoutSource, ...] = ()


def _norm_key(part_number: str, process_seq: str) -> tuple[str, str]:
    return (part_number.strip(), str(process_seq).strip())


def _uniq_sources(items: list[DieLayoutSource]) -> tuple[DieLayoutSource, ...]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[DieLayoutSource] = []
    for item in items:
        filename = (item.excel_filename or "").strip()
        supplier = (item.stamping_supplier or "").strip()
        number = (item.die_number or "").strip()
        version = (item.version or "").strip()
        key = (filename, supplier, number, version)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            DieLayoutSource(
                excel_filename=filename,
                stamping_supplier=supplier or None,
                die_number=number or None,
                version=version or None,
            )
        )
    unique.sort(
        key=lambda src: (
            src.stamping_supplier or "",
            src.version or "",
            src.excel_filename,
            src.die_number or "",
        )
    )
    return tuple(unique)


def _format_source_label(source: DieLayoutSource) -> str:
    filename = source.excel_filename or "（无文件名）"
    supplier = (source.stamping_supplier or "").strip()
    version = (source.version or "").strip()
    extras: list[str] = []
    if supplier:
        extras.append(supplier)
    if version:
        extras.append(f"版本 {version}")
    file_bit = f"{filename}（{'，'.join(extras)}）" if extras else filename
    number = (source.die_number or "").strip()
    if number:
        return f"{number} ← {file_bit}"
    return file_bit


def _source_suffix(sources: tuple[DieLayoutSource, ...]) -> str:
    if not sources:
        return ""
    joined = "；".join(_format_source_label(item) for item in sources)
    return f"。工艺确认表：{joined}"


def resolve_unique_die_number(candidates: set[str]) -> tuple[str | None, tuple[str, ...]]:
    """唯一非空编号。空集合 → missing；多个 → conflict。"""
    values = tuple(sorted(item.strip() for item in candidates if item and item.strip()))
    if not values:
        return None, ()
    unique = tuple(dict.fromkeys(values))
    if len(unique) == 1:
        return unique[0], ()
    return None, unique


def _index_traces(
    traces: list[StampingProcessTrace],
) -> tuple[
    set[str],
    set[tuple[str, str]],
    dict[tuple[str, str], set[str]],
    dict[str, tuple[DieLayoutSource, ...]],
    dict[tuple[str, str], tuple[DieLayoutSource, ...]],
    dict[tuple[str, str], tuple[DieLayoutSource, ...]],
]:
    part_numbers: set[str] = set()
    process_keys: set[tuple[str, str]] = set()
    number_groups: dict[tuple[str, str], set[str]] = {}
    part_raw: dict[str, list[DieLayoutSource]] = {}
    process_raw: dict[tuple[str, str], list[DieLayoutSource]] = {}
    numbered_raw: dict[tuple[str, str], list[DieLayoutSource]] = {}
    for trace in traces:
        part_number = trace.part_number.strip()
        process_seq = str(trace.process_seq).strip()
        if not part_number:
            continue
        key = (part_number, process_seq)
        part_numbers.add(part_number)
        process_keys.add(key)
        filename = (trace.excel_filename or "").strip()
        supplier = (trace.stamping_supplier or "").strip() or None
        version = (trace.version or "").strip() or None
        file_source = DieLayoutSource(
            excel_filename=filename,
            stamping_supplier=supplier,
            version=version,
        )
        part_raw.setdefault(part_number, []).append(file_source)
        process_raw.setdefault(key, []).append(file_source)
        number = (trace.die_number or "").strip()
        if number:
            number_groups.setdefault(key, set()).add(number)
            numbered_raw.setdefault(key, []).append(
                DieLayoutSource(
                    excel_filename=filename,
                    stamping_supplier=supplier,
                    die_number=number,
                    version=version,
                )
            )
    return (
        part_numbers,
        process_keys,
        number_groups,
        {part: _uniq_sources(items) for part, items in part_raw.items()},
        {key: _uniq_sources(items) for key, items in process_raw.items()},
        {key: _uniq_sources(items) for key, items in numbered_raw.items()},
    )


def validate_die_layout(
    rows: list[DieLayoutCheckRow],
    traces: list[StampingProcessTrace],
) -> tuple[dict[tuple[str, str], str], list[DieLayoutIssue]]:
    """
    对照冲压工艺库。
    找不到零件号 / 找不到工序 → 记问题。
    该行已有模具长或宽或高，却没有唯一模具编号 → 记问题。
    无尺寸的工序：有唯一编号则回填，没有则留空，不报错。
    """
    (
        parts_norm,
        keys_norm,
        number_groups,
        part_sources,
        process_sources,
        numbered_sources,
    ) = _index_traces(traces)
    merged: dict[tuple[str, str], DieLayoutCheckRow] = {}
    for row in rows:
        key = _norm_key(row.part_number, row.process_seq)
        if not key[0]:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = DieLayoutCheckRow(key[0], key[1], row.has_die_size)
        elif row.has_die_size and not existing.has_die_size:
            merged[key] = DieLayoutCheckRow(key[0], key[1], True)

    resolved: dict[tuple[str, str], str] = {}
    issues: list[DieLayoutIssue] = []
    seen_parts: set[str] = set()

    for key, row in merged.items():
        part_number, process_seq = key
        if part_number not in parts_norm:
            if part_number not in seen_parts:
                seen_parts.add(part_number)
                issues.append(
                    DieLayoutIssue(
                        kind="part_missing",
                        part_number=part_number,
                        process_seq=process_seq,
                    )
                )
            continue
        if key not in keys_norm:
            issues.append(
                DieLayoutIssue(
                    kind="process_missing",
                    part_number=part_number,
                    process_seq=process_seq,
                    sources=part_sources.get(part_number, ()),
                )
            )
            continue
        number, conflict = resolve_unique_die_number(number_groups.get(key, set()))
        if row.has_die_size:
            if conflict:
                issues.append(
                    DieLayoutIssue(
                        kind="die_number_conflict",
                        part_number=part_number,
                        process_seq=process_seq,
                        values=conflict,
                        sources=numbered_sources.get(key, ()),
                    )
                )
                continue
            if number is None:
                issues.append(
                    DieLayoutIssue(
                        kind="die_number_missing",
                        part_number=part_number,
                        process_seq=process_seq,
                        sources=process_sources.get(key, ()),
                    )
                )
                continue
            resolved[key] = number
            continue
        if number:
            resolved[key] = number
    return resolved, issues


def format_die_layout_issues(issues: list[DieLayoutIssue], *, limit: int = 30) -> str:
    if not issues:
        return ""
    counts = {
        "part_missing": 0,
        "process_missing": 0,
        "die_number_missing": 0,
        "die_number_conflict": 0,
    }
    for issue in issues:
        counts[issue.kind] += 1
    prefix = "核对失败。"
    if counts["part_missing"] or counts["process_missing"]:
        prefix = "核对失败：请先核对该基地+项目的冲压工艺确认表。"
    head = (
        f"{prefix}"
        f"共 {len(issues)} 处"
        f"（找不到零件号 {counts['part_missing']}，"
        f"找不到工序 {counts['process_missing']}，"
        f"有尺寸但无模具编号 {counts['die_number_missing']}，"
        f"编号不一致 {counts['die_number_conflict']}）："
    )
    lines: list[str] = [head]
    process_missing_by_part: dict[str, list[DieLayoutIssue]] = {}
    other_issues: list[DieLayoutIssue | tuple[str, list[DieLayoutIssue]]] = []
    for issue in issues:
        if issue.kind == "process_missing":
            bucket = process_missing_by_part.setdefault(issue.part_number, [])
            if not bucket:
                other_issues.append(("process_missing_group", bucket))
            bucket.append(issue)
        else:
            other_issues.append(issue)

    display_count = 0
    shown_issues = 0
    for item in other_issues:
        if display_count >= limit:
            break
        if isinstance(item, tuple):
            group = item[1]
            if not group:
                continue
            seqs = "、".join(entry.process_seq for entry in group)
            first = group[0]
            lines.append(
                f"零件 {first.part_number} 找不到工序 {seqs}" f"{_source_suffix(first.sources)}"
            )
            display_count += 1
            shown_issues += len(group)
            continue
        if item.kind == "part_missing":
            lines.append(f"找不到零件号 {item.part_number}（该基地+项目工艺库中没有）")
        elif item.kind == "die_number_conflict":
            joined = "、".join(item.values)
            lines.append(
                f"零件 {item.part_number} 工序 {item.process_seq} "
                f"已有模具长/宽/高，但冲压工艺模具编号不一致（{joined}）"
                f"{_source_suffix(item.sources)}"
            )
        else:
            lines.append(
                f"零件 {item.part_number} 工序 {item.process_seq} "
                f"已有模具长/宽/高，但冲压工艺没有模具编号"
                f"{_source_suffix(item.sources)}"
            )
        display_count += 1
        shown_issues += 1
    extra = len(issues) - shown_issues
    if extra > 0:
        lines.append(f"另有 {extra} 处未列出")
    return "\n".join(lines)
