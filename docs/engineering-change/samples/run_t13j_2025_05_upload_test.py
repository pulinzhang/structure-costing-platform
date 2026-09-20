"""芜湖 T13J · 2025-05 工程变更样表上传验收（同步跑 orchestrator）。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.common.audit import SYSTEM_USER  # noqa: E402
from app.database import DatabaseConfig  # noqa: E402
from app.exceptions.base import BusinessException  # noqa: E402
from app.repositories.engineering_change.upload_log_repository import (  # noqa: E402
    EngineeringChangeUploadLogInsert,
    EngineeringChangeUploadLogRepository,
)
from app.services.engineering_change.upload.orchestrator.orchestrator import (  # noqa: E402
    EngineeringChangeOrchestrator,
)
from app.services.engineering_change.upload.orchestrator.types import (  # noqa: E402
    EngineeringChangeExecuteArgs,
)
from app.services.file_trace.path_utils import to_upload_relpath  # noqa: E402
from app.services.file_trace.register import register_existing  # noqa: E402
from app.services.masterdata.vehicle_model.vehicle_model_service import (  # noqa: E402
    VehicleModelService,
)

logging.disable(logging.WARNING)

SAMPLES = Path(__file__).resolve().parent
LOCATION = "芜湖"
VEHICLE_MODEL = "T13J"
YEAR = 2025
MONTH = 5

SCENARIO_FILES = (
    "t13j-2025-05-stop.xlsx",
    "t13j-2025-05-rev-l1.xlsx",
    "t13j-2025-05-rev-l2.xlsx",
    "t13j-2025-05-not-install.xlsx",
    "t13j-2025-05-add-part.xlsx",
)


def _ensure_samples() -> None:
    missing = [name for name in SCENARIO_FILES if not (SAMPLES / name).is_file()]
    combined = SAMPLES / "t13j-2025-05-import-bundle.xlsx"
    if missing or not combined.is_file():
        if str(SAMPLES) not in sys.path:
            sys.path.insert(0, str(SAMPLES))
        from build_t13j_2025_05_import_bundles import main as build_main

        build_main()


def _save_and_register(db, file_content: bytes, filename: str):
    from app.common.timezone import now
    from app.config import settings

    stamp = now().strftime("%Y%m%d_%H%M%S")
    folder = (
        settings.UPLOAD_DIR / LOCATION / VEHICLE_MODEL / "engineering_change" / f"{YEAR}{MONTH:02d}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{stamp}_{filename}"
    target.write_bytes(file_content)
    upload_file = register_existing(
        db,
        file_category="engineering_change",
        stored_relpath=to_upload_relpath(target),
        original_filename=filename,
        current_user=SYSTEM_USER,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        year=YEAR,
        month=MONTH,
        supersede_same_scope=False,
    )
    return upload_file


def _run_one(db, path: Path) -> tuple[bool, str]:
    content = path.read_bytes()
    location, vehicle_model = VehicleModelService().require_introducible(
        db, LOCATION, VEHICLE_MODEL, YEAR, MONTH
    )
    upload_file = _save_and_register(db, content, path.name)
    audit_by = "system"
    log_row = EngineeringChangeUploadLogRepository().create(
        db,
        EngineeringChangeUploadLogInsert(
            upload_file_id=upload_file.id,
            location=location,
            vehicle_model=vehicle_model,
            customer_name="",
            effective_year=YEAR,
            effective_month=MONTH,
            original_filename=path.name,
            created_by=audit_by,
            updated_by=audit_by,
            status="pending",
        ),
    )
    db.commit()
    orchestrator = EngineeringChangeOrchestrator()
    try:
        result = orchestrator.execute(
            db,
            EngineeringChangeExecuteArgs(
                log_id=log_row.id,
                upload_file_id=upload_file.id,
                location=location,
                vehicle_model=vehicle_model,
                effective_year=YEAR,
                effective_month=MONTH,
                file_content=content,
            ),
            SYSTEM_USER,
        )
        db.commit()
        return True, f"OK change_orders={result.change_order_ids}"
    except (BusinessException, ValueError) as error:
        db.rollback()
        orchestrator.mark_log_failed(db, log_row.id, str(error), SYSTEM_USER)
        db.commit()
        return False, str(error)


def main() -> int:
    _ensure_samples()
    db = DatabaseConfig.get_session_factory()()
    failed = 0
    try:
        print(f"上传验收：{LOCATION} {VEHICLE_MODEL} {YEAR}-{MONTH:02d}\n")
        for name in SCENARIO_FILES:
            path = SAMPLES / name
            ok, message = _run_one(db, path)
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {name}")
            print(f"       {message}")
            if not ok:
                failed += 1
    finally:
        db.close()
    print(f"\n结果：{len(SCENARIO_FILES) - failed}/{len(SCENARIO_FILES)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
