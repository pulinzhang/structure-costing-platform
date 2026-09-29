"""钢价政策导出取数。"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.yishiyiyi.policy.filters import apply_export_filters


class SteelPricePolicyExport:
    """导出主表 / 扁平化行 / 明细统计。"""

    def list_policies_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[SteelPricePolicy]:
        """
        获取导出所需的主表数据（供 ExportService 调用）。

        Returns:
            政策主表列表（按年份、月份、ID 排序）
        """
        query = apply_export_filters(
            db.query(SteelPricePolicy),
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )

        query = query.order_by(
            SteelPricePolicy.year.asc(),
            SteelPricePolicy.month.asc(),
            SteelPricePolicy.id.asc(),
            SteelPricePolicy.steel_mill,
        )

        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def list_export_pairs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[tuple[SteelPricePolicy, SteelPriceLadderItem | None]]:
        """
        主表 LEFT JOIN 阶梯明细，按扁平化导出行分页。

        skip/limit 作用在联合行上（一条明细一行；无明细的政策占一行），
        与 count_export_rows / 预览页码对齐。
        """
        _base = (
            db.query(SteelPricePolicy, SteelPriceLadderItem)
            .select_from(SteelPricePolicy)
            .outerjoin(
                SteelPriceLadderItem,
                SteelPricePolicy.id == SteelPriceLadderItem.policy_id,
            )
        )
        query = apply_export_filters(
            _base,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )
        query = query.order_by(
            SteelPricePolicy.year.asc(),
            SteelPricePolicy.month.asc(),
            SteelPricePolicy.id.asc(),
            SteelPricePolicy.steel_mill,
            SteelPriceLadderItem.sort_order.asc(),
            SteelPriceLadderItem.id.asc(),
        )
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return [(policy, item) for policy, item in query.all()]

    def list_items_for_export(
        self,
        db: Session,
        policy_ids: list[int],
    ) -> list[SteelPriceLadderItem]:
        """
        根据政策 ID 列表获取明细数据（供 ExportService 调用）。

        Returns:
            明细列表（按 policy_id、sort_order、id 排序）
        """
        if not policy_ids:
            return []

        return (
            db.query(SteelPriceLadderItem)
            .filter(SteelPriceLadderItem.policy_id.in_(policy_ids))
            .order_by(
                SteelPriceLadderItem.policy_id,
                SteelPriceLadderItem.sort_order,
                SteelPriceLadderItem.id,
            )
            .all()
        )

    def count_policies_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
    ) -> int:
        """统计主表记录数（供 ExportService 调用）。"""
        query = apply_export_filters(
            db.query(func.count(SteelPricePolicy.id)),
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )
        return query.scalar() or 0

    def count_export_rows(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
    ) -> int:
        """
        统计扁平化导出行数（与 list_export_pairs 同一套 LEFT JOIN）。
        有明细的政策按明细条数计；无明细的政策计 1 行。
        """
        _base = (
            db.query(func.count(SteelPricePolicy.id))
            .select_from(SteelPricePolicy)
            .outerjoin(
                SteelPriceLadderItem,
                SteelPricePolicy.id == SteelPriceLadderItem.policy_id,
            )
        )
        query = apply_export_filters(
            _base,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )
        return query.scalar() or 0

    def count_items_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        policy_type: str | None = None,
    ) -> int:
        """
        统计明细总数（供统计接口调用）。
        通过 JOIN 主表并应用相同的过滤条件来确保一致性。
        """
        _base = db.query(func.count(SteelPriceLadderItem.id)).join(
            SteelPricePolicy,
            SteelPricePolicy.id == SteelPriceLadderItem.policy_id,
        )
        query = apply_export_filters(
            _base,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
            policy_type=policy_type,
        )
        return query.scalar() or 0
