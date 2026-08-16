"""一次性回填 stamping_parts 的 Excel 单元格溯源字段。

用法（仓库根目录）::

    python -X utf8 -m scripts.backfill_stamping_part_excel_provenance
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.stamping import StampingPart
from app.parsers.stamping.stamping_parser import parse_stamping_excel


def _find_source_file(
    location: str,
    vehicle_model: str,
    version: str,
    excel_filename: str,
) -> Path | None:
    upload_dir = settings.UPLOAD_DIR / location / vehicle_model / version
    if not upload_dir.is_dir():
        return None
    matches = sorted(
        [
            path
            for path in upload_dir.iterdir()
            if path.is_file() and path.name.endswith(excel_filename)
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def main() -> None:
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    try:
        parts = db.query(StampingPart).all()
        groups: dict[tuple[str, str, str, str], list[StampingPart]] = {}
        for part in parts:
            key = (
                part.location or "",
                part.vehicle_model or "",
                part.version or "",
                part.excel_filename or "",
            )
            groups.setdefault(key, []).append(part)

        updated = 0
        skipped = 0
        for (location, vehicle_model, version, excel_filename), group in groups.items():
            if not excel_filename:
                skipped += len(group)
                continue
            source = _find_source_file(location, vehicle_model, version, excel_filename)
            if source is None:
                print(f"[skip] 找不到源文件: {location}/{vehicle_model}/{version}/{excel_filename}")
                skipped += len(group)
                continue

            parse_result = parse_stamping_excel(str(source))
            by_part_number = {
                part.part_number: part
                for part in parse_result.parts
                if part.part_number
            }
            group_updated = 0
            for row in group:
                parsed = by_part_number.get(row.part_number)
                if not parsed:
                    continue
                row.excel_sheet_name = parsed.excel_sheet_name
                row.excel_row = parsed.excel_row
                row.excel_part_col = parsed.excel_part_col
                group_updated += 1
            updated += group_updated
            print(
                f"[ok] {excel_filename}: 更新 {group_updated}/{len(group)} "
                f"<- {source.name} sheet={parse_result.sheet_name!r}"
            )

        db.commit()
        print(f"完成: updated={updated}, skipped={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
