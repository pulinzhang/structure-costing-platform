"""写出工程变更导入样表：对照一本 + 五种改法各一份。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.services.engineering_change.upload.template_builder import (  # noqa: E402
    CHANGE_ORDER_SAMPLES,
    COMBINED_BOOK,
    SCENARIO_SAMPLES,
    TEMPLATE_FILENAME,
    TemplateBook,
    build_engineering_change_template,
)

SAMPLES = Path(__file__).resolve().parent
COMBINED_OUT = SAMPLES / "t28-2025-07-import-bundle.xlsx"


def _write_xlsx(path: Path, content: bytes) -> Path:
    temp_out = path.with_suffix(".building.xlsx")
    temp_out.write_bytes(content)
    try:
        temp_out.replace(path)
        return path
    except OSError:
        print(f"目标文件被占用，已写出: {temp_out}")
        return temp_out


def _print_book(path: Path, book: TemplateBook) -> None:
    types = [sample.change_type for sample in book.change_orders]
    process_numbers = list(dict.fromkeys(sample.part_number for sample in book.process))
    print(path.name)
    print(f"  工程变更单 {types}")
    print(f"  工艺新号={process_numbers}")


def main() -> None:
    content, filename = build_engineering_change_template()
    if filename != TEMPLATE_FILENAME:
        raise ValueError(f"模板文件名不是 {TEMPLATE_FILENAME}，得到 {filename}")
    combined_path = _write_xlsx(COMBINED_OUT, content)
    _print_book(combined_path, COMBINED_BOOK)

    if len(SCENARIO_SAMPLES) != len(CHANGE_ORDER_SAMPLES):
        raise ValueError("单场景文件数必须与变更单行数相同")
    for scenario in SCENARIO_SAMPLES:
        scenario_content, _ = build_engineering_change_template(scenario.book)
        scenario_path = _write_xlsx(SAMPLES / scenario.filename, scenario_content)
        _print_book(scenario_path, scenario.book)


if __name__ == "__main__":
    main()
