"""
厚度加减价导出服务
职责：主子表联合查询、数据扁平化、Excel 导出
被 SteelPricePolicyService 调用
"""

import logging

from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.yishiyiyi.policy import SteelPricePolicyRepository
from app.repositories.yishiyiyi.policy.dto import ExportRow
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.policy.export.excel_exporter import SteelPricePolicyExporter
from app.services.yishiyiyi.policy.filter_resolver import resolve_policy_category_filter

logger = logging.getLogger("service.steel_price_policy.export")


class SteelPricePolicyExportService:
    """厚度加减价导出服务"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()
        self._exporter = SteelPricePolicyExporter()

    @staticmethod
    def _resolved_scope(
        db: Session,
        *,
        category_name: str | None = None,
        grade_value: str | None = None,
    ) -> tuple[frozenset[str] | None, bool]:
        resolved = resolve_policy_category_filter(
            db,
            category_name=category_name,
            grade_value=grade_value,
        )
        return resolved.policy_category_names, resolved.no_match

    def get_export_data(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade_value: str | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[ExportRow]:
        """
        获取导出数据（主子表联合查询，返回扁平化的 ExportRow 列表）。

        Args:
            db: 数据库会话
            year: 筛选 - 年份
            month: 筛选 - 月份
            steel_mill: 筛选 - 钢厂
            category_name: 筛选 - 档案大类（冷轧/镀锌/酸洗）
            grade_value: 筛选 - 牌号（先解析档案大类再匹配政策）
            skip: 扁平化导出行偏移（一条阶梯明细一行）
            limit: 每页行数

        Returns:
            扁平化的导出行列表
        """
        category_names_in, category_filter_no_match = self._resolved_scope(
            db,
            category_name=category_name,
            grade_value=grade_value,
        )
        pairs = self.repository.list_export_pairs(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
            skip=skip,
            limit=limit,
        )
        return [self._to_export_row(policy, item) for policy, item in pairs]

    @staticmethod
    def _to_export_row(
        policy: SteelPricePolicy,
        item: SteelPriceLadderItem | None,
    ) -> ExportRow:
        """把主表 + 可选明细展成一行导出记录。"""
        return ExportRow(
            policy_id=policy.id,
            year=policy.year,
            month=policy.month,
            steel_mill=policy.steel_mill,
            category_name=policy.category_name or "",
            policy_type=policy.policy_type or "",
            grade_type=policy.grade_type,
            grade_value=policy.grade_value,
            base_thickness=str(policy.base_thickness)
            if policy.base_thickness is not None
            else None,
            excel_filename=policy.excel_filename,
            item_id=item.id if item is not None else None,
            target_sub_group=item.target_sub_group if item is not None else None,
            thick_min=str(item.thick_min)
            if item is not None and item.thick_min is not None
            else None,
            thick_min_operator=item.thick_min_operator if item is not None else None,
            thick_max=str(item.thick_max)
            if item is not None and item.thick_max is not None
            else None,
            thick_max_operator=item.thick_max_operator if item is not None else None,
            width_min=str(item.width_min)
            if item is not None and item.width_min is not None
            else None,
            width_min_operator=item.width_min_operator if item is not None else None,
            width_max=str(item.width_max)
            if item is not None and item.width_max is not None
            else None,
            width_max_operator=item.width_max_operator if item is not None else None,
            zinc_coating_min=(
                str(item.zinc_coating_min)
                if item is not None and item.zinc_coating_min is not None
                else None
            ),
            zinc_coating_min_operator=item.zinc_coating_min_operator if item is not None else None,
            zinc_coating_max=(
                str(item.zinc_coating_max)
                if item is not None and item.zinc_coating_max is not None
                else None
            ),
            zinc_coating_max_operator=item.zinc_coating_max_operator if item is not None else None,
            price_adjustment=item.price_adjustment if item is not None else None,
            is_base=item.is_base if item is not None else None,
            sort_order=item.sort_order if item is not None else None,
            excel_row=item.excel_row if item is not None else None,
            excel_col=item.excel_col if item is not None else None,
        )

    def count_export_data(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade_value: str | None = None,
    ) -> int:
        """
        统计导出数据总数（阶梯明细级别）。

        Args:
            db: 数据库会话
            year: 筛选 - 年份
            month: 筛选 - 月份
            steel_mill: 筛选 - 钢厂
            category_name: 筛选 - 档案大类（冷轧/镀锌/酸洗）
            grade_value: 筛选 - 牌号（先解析档案大类再匹配政策）

        Returns:
            明细总行数
        """
        category_names_in, category_filter_no_match = self._resolved_scope(
            db,
            category_name=category_name,
            grade_value=grade_value,
        )
        return self.repository.count_export_rows(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )

    def export_to_excel(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade_value: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        """
        生成导出 Excel 文件字节数据。

        Args:
            db: 数据库会话
            year: 筛选 - 年份
            month: 筛选 - 月份
            steel_mill: 筛选 - 钢厂
            category_name: 筛选 - 档案大类（冷轧/镀锌/酸洗）
            grade_value: 筛选 - 牌号（先解析档案大类再匹配政策）

        Returns:
            (文件字节数据, 文件名)
        """
        records = self.get_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_name=category_name,
            grade_value=grade_value,
        )
        return self._exporter.generate(
            records,
            year=year,
            month=month,
            steel_mill=steel_mill,
            current_user=current_user,
        )
