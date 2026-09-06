"""青岛 2025-01 引擎就绪冒烟（只读 get_ready）。"""

from __future__ import annotations

import json
import sys

from app.database import DatabaseConfig
from app.services.costing.engine.costing_engine_service import CostingEngineService


def main() -> int:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        svc = CostingEngineService()
        ready = svc.get_ready(db, location="青岛", year=2025, month=1)
        payload = ready.model_dump(exclude_none=True)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("---")
        print(f"can_start={ready.can_start} hard_stop={ready.gates.hard_stop}")
        print(f"vehicles={len(ready.plan.part_cost_scopes)} l0={len(ready.plan.l0_scopes)}")
        failed = [g for g in ready.gates.upload_or_config if not g.ok]
        if failed:
            print("HARD STOP items:")
            for item in failed:
                nav = item.navigate.page if item.navigate else "-"
                print(f"  - {item.code}: {item.message} -> #{nav}")
        will = [a for a in ready.gates.annual_derived if a.will_auto_calc]
        print(f"annual will_auto_calc={len(will)}")
        for item in will[:20]:
            print(f"  - {item.code} · {item.scope_key}")
        return 0 if ready.can_start else 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
