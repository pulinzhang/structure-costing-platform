"""一次性灌入现网已有冲压工厂全称（不是从下游 DISTINCT 发明身份）。

现网零件/加工费/核价/布点/文件溯源已出现的规范全称共 5 家。
ERP 代码现网没有，按模板形态暂编（创建后界面不能改）。

用法（仓库根目录）::

    python -X utf8 -m scripts.import_current_suppliers
"""

from __future__ import annotations

from app.common.audit import SYSTEM_USER
from app.database import DatabaseConfig
from app.exceptions.base import BusinessException
from app.schemas.dto.supplier_dto import SupplierCreateDTO
from app.services.masterdata.supplier.supplier_service import SupplierService

# 缩写只给人看；全称对齐现网工艺列；别名吃短写/曾用名。
CURRENT_SUPPLIERS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("海众", "烟台海众汽车零部件有限公司", "HZ001", ("烟台海众",)),
    ("全鑫", "芜湖全鑫模具机械股份有限公司", "QX001", ("芜湖全鑫",)),
    ("振华", "安徽振华汽车部件有限责任公司", "ZH001", ("安徽振华",)),
    ("常庆", "安庆常庆汽车部件有限公司", "CQ001", ("安庆常庆", "常庆汽配")),
    ("贝奇", "昆山贝奇精密机械有限公司安庆分公司", "BQ001", ("昆山贝奇", "贝奇安庆分公司")),
)


def import_current_suppliers() -> None:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    service = SupplierService()
    created = 0
    skipped = 0
    try:
        for abbreviation, full_name, erp_code, aliases in CURRENT_SUPPLIERS:
            existing = service.repository.get_by_full_name(db, full_name)
            if existing is not None:
                print(f"跳过（已有全称）：{full_name}")
                skipped += 1
                continue
            try:
                vo = service.create(
                    db,
                    SupplierCreateDTO(
                        abbreviation=abbreviation,
                        full_name=full_name,
                        erp_code=erp_code,
                        aliases=list(aliases),
                    ),
                    current_user=SYSTEM_USER,
                )
            except BusinessException as exc:
                print(f"失败：{full_name} — {exc.message}")
                raise
            print(f"新增：{vo.abbreviation} / {vo.full_name} / {vo.erp_code}")
            created += 1
        print(f"完成：新增 {created}，跳过 {skipped}。")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_current_suppliers()
