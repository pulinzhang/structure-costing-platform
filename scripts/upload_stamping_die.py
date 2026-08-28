"""同步上传冲压模具布点清单（校验失败不覆盖已有库）。

默认传芜湖 T13J 样本。改完 Excel 后在仓库根目录再跑同一条命令即可。

用法::

    python -X utf8 -m scripts.upload_stamping_die
    python -X utf8 -m scripts.upload_stamping_die --file excel_sample/T13J/你改过的文件.xlsx
    python -X utf8 -m scripts.upload_stamping_die --location 芜湖 --vehicle-model T13J --file path.xlsx
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import app.models  # noqa: F401
from app.common.audit import SYSTEM_USER
from app.database import DatabaseConfig
from app.exceptions.base import BusinessException
from app.services.stamping.die.upload_service import StampingDieUploadService

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCATION = "芜湖"
DEFAULT_VEHICLE_MODEL = "T13J"
DEFAULT_FILE = ROOT / "excel_sample" / "T13J" / "副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx"


def _quiet_sqlalchemy() -> None:
    logging.disable(logging.CRITICAL)
    engine = DatabaseConfig.get_engine()
    engine.echo = False
    logging.getLogger("sqlalchemy.engine").disabled = True
    logging.getLogger("sqlalchemy.pool").disabled = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="上传冲压模具布点清单")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help="采购基地")
    parser.add_argument("--vehicle-model", default=DEFAULT_VEHICLE_MODEL, help="项目")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help="模具布点 Excel 路径",
    )
    args = parser.parse_args(argv)

    excel_path = args.file if args.file.is_absolute() else ROOT / args.file
    if not excel_path.is_file():
        print(f"文件不存在：{excel_path}", file=sys.stderr)
        return 1

    _quiet_sqlalchemy()
    print(f"基地 {args.location}  项目 {args.vehicle_model}", flush=True)
    print(f"文件 {excel_path}", flush=True)

    db = DatabaseConfig.get_session_factory()()
    try:
        result = StampingDieUploadService(db).process_upload(
            file_content=excel_path.read_bytes(),
            filename=excel_path.name,
            location=args.location,
            vehicle_model=args.vehicle_model,
            current_user=SYSTEM_USER,
        )
        print(
            f"已入库 {result.parts_count} 零件 / {result.processes_count} 工序 "
            f"{result.location} {result.vehicle_model}",
            flush=True,
        )
        return 0
    except BusinessException as error:
        print("未入库，请改 Excel 后重跑本脚本：", flush=True)
        print(str(error), flush=True)
        return 1
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
