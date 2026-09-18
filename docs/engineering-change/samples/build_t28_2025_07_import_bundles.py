"""写出工程变更对照样表（五种改法 + 后围同一总成合写）。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.services.engineering_change.upload.template_builder import (  # noqa: E402
    CHANGE_ORDER_SAMPLES,
    PROCESS_SAMPLES,
    TEMPLATE_FILENAME,
    build_engineering_change_template,
)

SAMPLES = Path(__file__).resolve().parent
OUT = SAMPLES / "t28-2025-07-import-bundle.xlsx"


def main() -> None:
    content, filename = build_engineering_change_template()
    if filename != TEMPLATE_FILENAME:
        raise ValueError(f"模板文件名不是 {TEMPLATE_FILENAME}，得到 {filename}")
    temp_out = OUT.with_suffix(".building.xlsx")
    temp_out.write_bytes(content)
    try:
        temp_out.replace(OUT)
        path = OUT
    except OSError:
        print(f"目标文件被占用，已写出: {temp_out}")
        path = temp_out
    types = [sample.change_type for sample in CHANGE_ORDER_SAMPLES]
    process_numbers = list(dict.fromkeys(sample.part_number for sample in PROCESS_SAMPLES))
    print(path.name)
    print(f"  工程变更单 {types}")
    print(f"  工艺新号={process_numbers}")


if __name__ == "__main__":
    main()
