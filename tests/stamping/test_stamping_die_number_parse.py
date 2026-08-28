"""可选：四份 T13J 工艺确认表能映射模具编号列。"""

from pathlib import Path

import pytest

from app.parsers.stamping.stamping_parser import parse_stamping_excel

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "excel_sample" / "T13J"
_PROCESS_FILES = (
    "T13J冲压工艺确认表-常庆.xlsx",
    "T13J项目冲压工艺确认表-全鑫.xlsx",
    "T13J项目冲压工艺确认表-振华-V3-01版.xlsx",
    "T13J项目冲压工艺确认表-贝奇.xlsx",
)


def _available_process_files() -> list[Path]:
    return [path for name in _PROCESS_FILES if (path := _SAMPLE_DIR / name).is_file()]


@pytest.mark.skipif(not _available_process_files(), reason="T13J 工艺确认表未放入 excel_sample")
def test_t13j_process_files_map_die_number_column() -> None:
    files = _available_process_files()
    assert len(files) == len(_PROCESS_FILES)
    filled_total = 0
    for sample in files:
        result = parse_stamping_excel(str(sample))
        assert "die_number" in result.col_map, sample.name
        assert result.processes, sample.name
        filled_total += sum(1 for item in result.processes if item.die_number)
    assert filled_total > 0
