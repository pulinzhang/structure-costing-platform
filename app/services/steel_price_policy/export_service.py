"""
厚度加减价导出服务
职责：主子表联合查询、数据扁平化、Excel 导出
被 SteelPricePolicyService 调用
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.steel_price_policy import SteelPricePolicyRepository
from app.schemas.dto.steel_price_policy_dto import ExportRow
from app.services.steel_price_policy.excel_exporter import SteelPricePolicyExporter


logger = logging.getLogger("service.steel_price_policy.export")


class SteelPricePolicyExportService:
    """厚度加减价导出服务"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()
        self._exporter = SteelPricePolicyExporter()

    def get_export_data(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> list[ExportRow]:
        """
        获取导出数据（主子表联合查询，返回扁平化的 ExportRow 列表）。

        Args:
            db: 数据库会话
            year: 筛选 - 年份
            month: 筛选 - 月份
            steel_mill: 筛选 - 钢厂
            skip: 分页偏移
            limit: 分页限制

        Returns:
            扁平化的导出行列表
        """
        policies = self.repository.list_policies_for_export(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            skip=skip,
            limit=limit,
        )

        if not policies:
            return []

        policy_ids = [p.id for p in policies]
        items_map: dict[int, list] = {}
        items = self.repository.list_items_for_export(db, policy_ids)
        for item in items:
            items_map.setdefault(item.policy_id, []).append(item)

        rows: list[ExportRow] = []
        for policy in policies:
            policy_items = items_map.get(policy.id, [])
            if not policy_items:
                rows.append(
                    ExportRow(
                        policy_id=policy.id,
                        year=policy.year,
                        month=policy.month,
                        steel_mill=policy.steel_mill,
                        category_name=policy.category_name or "",
                        policy_type=policy.policy_type or "",
                        grade_type=policy.grade_type,
                        grade_value=policy.grade_value,
                        base_thickness=str(policy.base_thickness) if policy.base_thickness is not None else None,
                        excel_filename=policy.excel_filename,
                    )
                )
            else:
                for item in policy_items:
                    rows.append(
                        ExportRow(
                            policy_id=policy.id,
                            year=policy.year,
                            month=policy.month,
                            steel_mill=policy.steel_mill,
                            category_name=policy.category_name or "",
                            policy_type=policy.policy_type or "",
                            grade_type=policy.grade_type,
                            grade_value=policy.grade_value,
                            base_thickness=str(policy.base_thickness) if policy.base_thickness is not None else None,
                            item_id=item.id,
                            target_sub_group=item.target_sub_group,
                            thick_min=str(item.thick_min) if item.thick_min is not None else None,
                            thick_min_operator=item.thick_min_operator,
                            thick_max=str(item.thick_max) if item.thick_max is not None else None,
                            thick_max_operator=item.thick_max_operator,
                            width_min=str(item.width_min) if item.width_min is not None else None,
                            width_min_operator=item.width_min_operator,
                            width_max=str(item.width_max) if item.width_max is not None else None,
                            width_max_operator=item.width_max_operator,
                            zinc_coating_min=str(item.zinc_coating_min) if item.zinc_coating_min is not None else None,
                            zinc_coating_min_operator=item.zinc_coating_min_operator,
                            zinc_coating_max=str(item.zinc_coating_max) if item.zinc_coating_max is not None else None,
                            zinc_coating_max_operator=item.zinc_coating_max_operator,
                            price_adjustment=item.price_adjustment,
                            is_base=item.is_base,
                            sort_order=item.sort_order,
                            excel_filename=policy.excel_filename,
                            excel_row=item.excel_row,
                            excel_col=item.excel_col,
                        )
                    )

        return rows

    def count_export_data(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """
        统计导出数据总数（阶梯明细级别）。

        Args:
            db: 数据库会话
            year: 筛选 - 年份
            month: 筛选 - 月份
            steel_mill: 筛选 - 钢厂

        Returns:
            明细总行数
        """
        return self.repository.count_items_for_export(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )

    def export_to_excel(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """
        生成导出 Excel 文件字节数据。

        Args:
            db: 数据库会话
            year: 筛选 - 年份
            month: 筛选 - 月份
            steel_mill: 筛选 - 钢厂

        Returns:
            (文件字节数据, 文件名)
        """
        records = self.get_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )
        return self._exporter.generate(
            records,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )
