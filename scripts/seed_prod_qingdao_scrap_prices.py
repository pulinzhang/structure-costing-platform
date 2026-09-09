"""
生产服务器：灌青岛废料月度价（钢材 + 铝板）。

数字与开发种子 ``seed_stamping_scrap_prices`` 相同，但只写青岛。
目标库是当前环境 ``DATABASE_URL``（生产机上的 `.env`）。不要拷开发库文件。

先停服务；你已删库 / 新代码建表之后，基地只留青岛。然后在仓库根目录::

    python -X utf8 -m scripts.seed_prod_qingdao_scrap_prices

不要在生产跑 ``seed_stamping_scrap_prices``（会按多座基地写价）。
"""

from __future__ import annotations

from app import models as _models  # noqa: F401
from app.common.audit import SYSTEM_USER, audit_create, audit_update
from app.database import DatabaseConfig
from app.models.masterdata.location import Location, LocationAlias
from app.models.yishiyiyi import StampingScrapPrice
from app.services.masterdata.location.location_service import LocationService
from scripts.seed_stamping_scrap_prices import build_seed_rows

QINGDAO = "青岛"
QINGDAO_ALIAS = "青岛基地"
QINGDAO_SORT = 4


def _ensure_qingdao_only_location(db) -> None:
    names = LocationService().list_registered(db)
    extra = [name for name in names if name != QINGDAO]
    if extra:
        raise RuntimeError(
            "生产只灌青岛，但 locations 还有其它基地："
            + "、".join(extra)
            + "。先在基地页删掉，或确认这就是要留的库。"
        )
    if QINGDAO in names:
        return
    db.add(
        Location(
            location=QINGDAO,
            is_enabled=True,
            sort_order=QINGDAO_SORT,
            created_by=SYSTEM_USER,
            updated_by=SYSTEM_USER,
        )
    )
    if db.get(LocationAlias, QINGDAO_ALIAS) is None:
        db.add(LocationAlias(alias=QINGDAO_ALIAS, location=QINGDAO))
    db.flush()
    print(f"已写入基地 {QINGDAO}（未灌大连/芜湖/鄂尔多斯）")


def seed_qingdao_scrap_prices() -> None:
    DatabaseConfig.create_tables()
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    create_audit = audit_create(SYSTEM_USER)
    update_audit = audit_update(SYSTEM_USER)

    try:
        _ensure_qingdao_only_location(db)
        rows = [payload for payload in build_seed_rows([QINGDAO]) if payload["location"] == QINGDAO]
        if not rows:
            raise RuntimeError("没有青岛种子行")
        print(f"准备写入青岛 {len(rows)} 条（钢材+铝板）...")
        created = 0
        updated = 0
        for payload in rows:
            if payload["location"] != QINGDAO:
                raise RuntimeError(f"拒绝写入非青岛：{payload['location']}")
            existing = (
                db.query(StampingScrapPrice)
                .filter(
                    StampingScrapPrice.location == payload["location"],
                    StampingScrapPrice.scrap_category == payload["scrap_category"],
                    StampingScrapPrice.year == payload["year"],
                    StampingScrapPrice.month == payload["month"],
                )
                .first()
            )
            if existing:
                existing.market_price = payload["market_price"]
                existing.deduction_fee = payload["deduction_fee"]
                existing.net_price = payload["net_price"]
                existing.remark = payload["remark"]
                existing.updated_by = update_audit["updated_by"]
                updated += 1
            else:
                db.add(StampingScrapPrice(**payload, **create_audit))
                created += 1
        leftover = (
            db.query(StampingScrapPrice.id).filter(StampingScrapPrice.location != QINGDAO).count()
        )
        if leftover:
            raise RuntimeError(f"库里还有非青岛废料价 {leftover} 条，已回滚")
        db.commit()
        print(f"完成：新增 {created} 条，更新 {updated} 条。")
    except Exception as exc:
        db.rollback()
        print(f"失败，已回滚：{exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_qingdao_scrap_prices()
