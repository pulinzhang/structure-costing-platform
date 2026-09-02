"""校验各上传页下载模板能否被对应 Parser 解析。"""

from __future__ import annotations

import tempfile
from pathlib import Path


def main() -> None:
    failures: list[str] = []

    # 1 冲压工艺
    from app.parsers.stamping.stamping_parser import parse_stamping_excel
    from app.services.stamping.upload.template_builder import (
        build_stamping_process_template,
    )

    content, name = build_stamping_process_template()
    path = Path(tempfile.gettempdir()) / name
    path.write_bytes(content)
    result = parse_stamping_excel(str(path))
    ok = len(result.parts) >= 3 and len(result.processes) >= 6
    print(
        f"[1] 冲压工艺: parts={len(result.parts)} processes={len(result.processes)} "
        f"vehicle={result.vehicle_model!r} ver={result.version!r} -> {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        failures.append("冲压工艺")

    # 2 BOM
    from app.parsers.bom.bom_parser import parse_bom_excel
    from app.services.bom.bom_template_builder import build_bom_material_template

    content, name = build_bom_material_template()
    bom = parse_bom_excel(content)
    ok = len(bom.nodes) >= 4 and bom.meta.vehicle_model == "T28"
    print(
        f"[2] 材料清单: nodes={len(bom.nodes)} vehicle={bom.meta.vehicle_model!r} "
        f"ver={bom.meta.bom_version!r} -> {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        failures.append("材料清单")

    # 3 加减价
    from app.parsers.yishiyiyi.policy import parse_steel_price_policy_excel
    from app.services.yishiyiyi.policy.importing.template_builder import (
        build_steel_price_policy_template,
    )

    content, name = build_steel_price_policy_template()
    policy = parse_steel_price_policy_excel(content, year=2025, month=1)
    thickness_count = sum(1 for item in policy.policies if item.policy_type == "THICKNESS")
    ok = thickness_count >= 4
    print(
        f"[3] 加减价政策: policies={len(policy.policies)} thickness={thickness_count} "
        f"warnings={len(getattr(policy, 'warnings', []) or [])} -> {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        failures.append("加减价政策")

    # 4 基准价
    from app.parsers.yishiyiyi.base_price import parse_base_price_excel
    from app.services.yishiyiyi.base_price.importing.template_builder import (
        build_steel_base_price_template,
    )

    content, name = build_steel_base_price_template()
    base = parse_base_price_excel(content)
    locations = sorted({str(row.get("location")) for row in base.records})
    ok = len(base.records) >= 8 and not base.errors
    print(
        f"[4] 基准价格: records={len(base.records)} locations={locations} "
        f"errors={base.errors} -> {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        failures.append("基准价格")

    # 5 冲次单价
    from app.parsers.stamping.tonnage_price_parser import parse_tonnage_price_excel
    from app.services.stamping.tonnage_price_import_service import (
        StampingTonnagePriceImportService,
    )

    content, name = StampingTonnagePriceImportService().build_template()
    tonnage = parse_tonnage_price_excel(content)
    ok = len(tonnage.rows) >= 3
    print(
        f"[5] 冲次单价: rows={len(tonnage.rows)} errors={tonnage.errors} "
        f"-> {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        failures.append("冲次单价")

    # 6 焊接单价
    from app.parsers.bom.welding_unit_price_parser import parse_welding_unit_price_excel
    from app.services.bom.welding_unit_price.import_service import (
        BomWeldingUnitPriceImportService,
    )

    content, name = BomWeldingUnitPriceImportService().build_template()
    welding = parse_welding_unit_price_excel(content)
    ok = len(welding.rows) >= 3
    print(
        f"[6] 焊接单价: rows={len(welding.rows)} errors={welding.errors} "
        f"-> {'OK' if ok else 'FAIL'}"
    )
    if not ok:
        failures.append("焊接单价")

    # 7 年度零件价：须指定基地+年度，零件来自 BOM 外购叶子
    print("[7] 年度零件价: SKIP（须指定基地+年度，零件来自 BOM 外购叶子）")

    # 8 包装运输费
    from app.parsers.bom.packaging_transport_fee_parser import (
        parse_packaging_transport_fee_excel,
    )
    from app.services.bom.packaging_transport_fee.import_service import (
        BomPackagingTransportFeeImportService,
    )

    content, name = BomPackagingTransportFeeImportService().build_template()
    packaging = parse_packaging_transport_fee_excel(content)
    ok = len(packaging.rows) >= 1
    print(f"[8] 包装运输费: rows={len(packaging.rows)} " f"-> {'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append("包装运输费")

    print()
    if failures:
        print("FAILED:", ", ".join(failures))
        raise SystemExit(1)
    print("ALL TEMPLATES PARSE OK — 格式与上传 Parser 匹配")


if __name__ == "__main__":
    main()
