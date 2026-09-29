"""系统设置业务逻辑。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.money import Q2, Q4, Q6, quantize_money
from app.common.system_defaults import (
    DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
    DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
    DEFAULT_BODY_PANEL_MAX_THICKNESS,
    DEFAULT_FINISHED_FINANCE_RATE,
    DEFAULT_FINISHED_MANAGEMENT_RATE,
    DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
    DEFAULT_FINISHED_SCRAP_RATE,
    DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
    DEFAULT_MATERIAL_LOSS_RATE,
    DEFAULT_SCRAP_RECOVERY_RATE,
    DEFAULT_STEEL_DENSITY,
    DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
)
from app.config import settings as app_settings
from app.repositories.settings.login_security_repository import LoginSecurityRepository
from app.repositories.settings.system.system_config_repository import SystemConfigRepository
from app.schemas.dto.settings_dto import (
    SystemConfigPatch,
    SystemConfigUpdateDTO,
    SystemConfigWrite,
)
from app.schemas.vo.settings_vo import ConfigVO
from app.schemas.vo.user_vo import UserVO

DEFAULT_APP_NAME = "结构件自动核价平台"
LEGACY_APP_NAMES = frozenset(
    {
        "汽车冲压件自动核价平台",
        "冲压件自动核价平台",
    }
)
SAMPLE_PROCUREMENT_AGREEMENT_REMARKS = (
    "1、本附件为双方签署的《{company_name}采购主合同》（编号：__________________）\n"
    "不可分割的部分，经双方签字、盖章后生效。\n"
    "双方同意，除合同零部件价格条款按本附件执行外，其他所有条款继续有效，直至双方签订新的采购主合同。\n"
    "\n"
    "2、如工装费用单独支付，\n"
    "具体支付方式以双方签订的编号为：__________________《工装支付协议》。\n"
    "\n"
    "3、工装费用分摊数量达到以上合同约定分摊数量时，双方确认分摊数量后工装费自动剥离，并于分摊完毕立即执行新结算价格；\n"
    "特殊情况时工装费用剥离最终以报告为准。\n"
    "\n"
    "4、如上合同产品清单中，乙方开发 / 项目 / 个产品，涉及工装费金额 / 元，于 / 年年度价格中已清算（具体详见产品备注）。\n"
    "□甲方所有，在乙方现场供生产备用 □乙方所有 □甲乙双方共有。\n"
    "未经甲方确认同意，乙方不得私自处置。\n"
    "\n"
    "5、上述价格执行有效期为{start_year}年{start_month}月1日起至"
    "{end_year}年{end_month}月{end_day}日。\n"
    "\n"
    "6、结算方式及付款期限：货到甲方经检验合格入寄库存，以甲方实际出库使用量结算；\n"
    "甲方在接到乙方增值税发票后90个工作日内以承兑汇票或现金转账方式付款。\n"
    "\n"
    "7、以上零部件价格均为含运输费、包装费、仓储费、分拣费、配送费，\n"
    "不含13%增值税的我方入库价格。\n"
    "\n"
    "8、供货方式（必选项）：乙方直供□普威技研 □普威新材料 □普威轻量化 □普威滨江 □安徽部件 □安庆普威 □湖南普威 □普威陕西\n"
    "□普威江西 □鄂尔多斯普威 □山东普威 □湖州普威 □金华普威 □济南普威 □轻量化弋江工厂 □其他（如选其他需备注清楚）。\n"
    "\n"
    "9、因乙方的分供方不能正常供货，导致乙方不能按照双方约定向甲方供货或者存在供货风险的，\n"
    "甲方有权暂停支付乙方的货款，直至乙方恢复正常供货或者消除前述供货风险。\n"
    "\n"
    "10、本附件签署原件叁份，甲方执贰份，乙方执壹份。"
)
APP_VERSION = "1.0.0"


class SettingsService:
    """系统配置：单例读写 + 核价用参数读取。"""

    def __init__(self) -> None:
        self.repository = SystemConfigRepository()
        self.login_security_repo = LoginSecurityRepository()

    @staticmethod
    def _display_app_name(raw: str | None) -> str:
        name = (raw or "").strip()
        if not name or name in LEGACY_APP_NAMES:
            return DEFAULT_APP_NAME
        return name

    def get_config(self, db: Session, aux_db: Session | None = None) -> ConfigVO:
        login_lock_minutes = self._login_lock_minutes(aux_db)
        row = self.repository.get_singleton(db)
        if row is None:
            return ConfigVO(
                app_name=SettingsService._display_app_name(
                    app_settings.APP_NAME or DEFAULT_APP_NAME
                ),
                company_name="",
                procurement_agreement_remarks="",
                procurement_agreement_remarks_sample=SAMPLE_PROCUREMENT_AGREEMENT_REMARKS,
                version=APP_VERSION,
                steel_density=DEFAULT_STEEL_DENSITY,
                material_loss_rate=DEFAULT_MATERIAL_LOSS_RATE,
                scrap_recovery_rate=DEFAULT_SCRAP_RECOVERY_RATE,
                finished_finance_rate=DEFAULT_FINISHED_FINANCE_RATE,
                finished_management_rate=DEFAULT_FINISHED_MANAGEMENT_RATE,
                finished_warehouse_packaging_rate=DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
                finished_scrap_rate=DEFAULT_FINISHED_SCRAP_RATE,
                finished_pretax_profit_rate=DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
                swing_shear_process_fee_per_ton=DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
                base_price_month_move_limit=DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
                base_price_processing_fee_limit=DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
                body_panel_max_thickness=DEFAULT_BODY_PANEL_MAX_THICKNESS,
                login_lock_minutes=login_lock_minutes,
            )
        return ConfigVO(
            app_name=SettingsService._display_app_name(row.app_name),
            company_name=self._strip_text(getattr(row, "company_name", None)),
            procurement_agreement_remarks=self._strip_text(
                getattr(row, "procurement_agreement_remarks", None)
            ),
            procurement_agreement_remarks_sample=SAMPLE_PROCUREMENT_AGREEMENT_REMARKS,
            version=APP_VERSION,
            steel_density=self._normalize_density(row.steel_density),
            material_loss_rate=self._normalize_loss_rate(getattr(row, "material_loss_rate", None)),
            scrap_recovery_rate=self._normalize_recovery_rate(
                getattr(row, "scrap_recovery_rate", None)
            ),
            finished_finance_rate=self._normalize_percent_rate(
                getattr(row, "finished_finance_rate", None),
                DEFAULT_FINISHED_FINANCE_RATE,
            ),
            finished_management_rate=self._normalize_percent_rate(
                getattr(row, "finished_management_rate", None),
                DEFAULT_FINISHED_MANAGEMENT_RATE,
            ),
            finished_warehouse_packaging_rate=self._normalize_percent_rate(
                getattr(row, "finished_warehouse_packaging_rate", None),
                DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
            ),
            finished_scrap_rate=self._normalize_permille_rate(
                getattr(row, "finished_scrap_rate", None),
                DEFAULT_FINISHED_SCRAP_RATE,
            ),
            finished_pretax_profit_rate=self._normalize_percent_rate(
                getattr(row, "finished_pretax_profit_rate", None),
                DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
            ),
            swing_shear_process_fee_per_ton=self._normalize_non_negative_q2(
                getattr(row, "swing_shear_process_fee_per_ton", None),
                DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
            ),
            base_price_month_move_limit=self._normalize_non_negative_q2(
                getattr(row, "base_price_month_move_limit", None),
                DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
            ),
            base_price_processing_fee_limit=self._normalize_non_negative_q2(
                getattr(row, "base_price_processing_fee_limit", None),
                DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
            ),
            body_panel_max_thickness=self._normalize_non_negative_q2(
                getattr(row, "body_panel_max_thickness", None),
                DEFAULT_BODY_PANEL_MAX_THICKNESS,
            ),
            login_lock_minutes=login_lock_minutes,
        )

    def _login_lock_minutes(self, aux_db: Session | None) -> int:
        if aux_db is None:
            return 15
        return self.login_security_repo.get_lock_minutes(aux_db)

    def update_config(
        self,
        db: Session,
        aux_db: Session,
        dto: SystemConfigUpdateDTO,
        current_user: UserVO,
    ) -> ConfigVO:
        updated_by = audit_update(current_user)["updated_by"] or ""
        self.login_security_repo.save_lock_minutes(aux_db, dto.login_lock_minutes, updated_by)
        aux_db.commit()
        app_name = SettingsService._display_app_name(dto.app_name)
        company_name = dto.company_name
        remarks = dto.procurement_agreement_remarks
        audit = audit_create(current_user)
        steel_density = quantize_money(dto.steel_density, Q4)
        material_loss_rate = quantize_money(dto.material_loss_rate, Q6)
        scrap_recovery_rate = quantize_money(dto.scrap_recovery_rate, Q6)
        finished_finance_rate = quantize_money(dto.finished_finance_rate, Q6)
        finished_management_rate = quantize_money(dto.finished_management_rate, Q6)
        finished_warehouse_packaging_rate = quantize_money(
            dto.finished_warehouse_packaging_rate, Q6
        )
        finished_scrap_rate = quantize_money(dto.finished_scrap_rate, Q6)
        finished_pretax_profit_rate = quantize_money(dto.finished_pretax_profit_rate, Q6)
        swing_shear_process_fee_per_ton = quantize_money(dto.swing_shear_process_fee_per_ton, Q2)
        base_price_month_move_limit = quantize_money(dto.base_price_month_move_limit, Q2)
        base_price_processing_fee_limit = quantize_money(dto.base_price_processing_fee_limit, Q2)
        body_panel_max_thickness = quantize_money(dto.body_panel_max_thickness, Q2)
        row = self.repository.get_singleton(db)
        if row is None:
            self.repository.create_singleton(
                db,
                SystemConfigWrite(
                    app_name=app_name,
                    company_name=company_name,
                    procurement_agreement_remarks=remarks,
                    steel_density=steel_density,
                    material_loss_rate=material_loss_rate,
                    scrap_recovery_rate=scrap_recovery_rate,
                    finished_finance_rate=finished_finance_rate,
                    finished_management_rate=finished_management_rate,
                    finished_warehouse_packaging_rate=finished_warehouse_packaging_rate,
                    finished_scrap_rate=finished_scrap_rate,
                    finished_pretax_profit_rate=finished_pretax_profit_rate,
                    swing_shear_process_fee_per_ton=swing_shear_process_fee_per_ton,
                    base_price_month_move_limit=base_price_month_move_limit,
                    base_price_processing_fee_limit=base_price_processing_fee_limit,
                    body_panel_max_thickness=body_panel_max_thickness,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
        else:
            self.repository.update_singleton(
                db,
                row,
                SystemConfigPatch(
                    app_name=app_name,
                    company_name=company_name,
                    procurement_agreement_remarks=remarks,
                    steel_density=steel_density,
                    material_loss_rate=material_loss_rate,
                    scrap_recovery_rate=scrap_recovery_rate,
                    finished_finance_rate=finished_finance_rate,
                    finished_management_rate=finished_management_rate,
                    finished_warehouse_packaging_rate=finished_warehouse_packaging_rate,
                    finished_scrap_rate=finished_scrap_rate,
                    finished_pretax_profit_rate=finished_pretax_profit_rate,
                    swing_shear_process_fee_per_ton=swing_shear_process_fee_per_ton,
                    base_price_month_move_limit=base_price_month_move_limit,
                    base_price_processing_fee_limit=base_price_processing_fee_limit,
                    body_panel_max_thickness=body_panel_max_thickness,
                    updated_by=audit_update(current_user)["updated_by"],
                ),
            )
        db.commit()
        return self.get_config(db, aux_db)

    def get_steel_density(self, db: Session) -> Decimal:
        """核价用：读系统配置密度，无效或缺失则回退 7.85。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_STEEL_DENSITY
        return self._normalize_density(row.steel_density)

    def get_material_loss_rate(self, db: Session) -> Decimal:
        """核价用：读冲压材料损耗率，无效或缺失则回退 0.003（千分之3）。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_MATERIAL_LOSS_RATE
        return self._normalize_loss_rate(getattr(row, "material_loss_rate", None))

    def get_scrap_recovery_rate(self, db: Session) -> Decimal:
        """核价用：读废料回收率，无效或缺失则回退 0.97。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_SCRAP_RECOVERY_RATE
        return self._normalize_recovery_rate(getattr(row, "scrap_recovery_rate", None))

    def get_finished_finance_rate(self, db: Session) -> Decimal:
        """核价用：读成品财务费率，无效或缺失则回退 0.02。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_FINANCE_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_finance_rate", None),
            DEFAULT_FINISHED_FINANCE_RATE,
        )

    def get_finished_management_rate(self, db: Session) -> Decimal:
        """核价用：读成品管理费率，无效或缺失则回退 0.02。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_MANAGEMENT_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_management_rate", None),
            DEFAULT_FINISHED_MANAGEMENT_RATE,
        )

    def get_finished_warehouse_packaging_rate(self, db: Session) -> Decimal:
        """核价用：读仓储+包装管理费用率，无效或缺失则回退 0.01。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_warehouse_packaging_rate", None),
            DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
        )

    def get_finished_scrap_rate(self, db: Session) -> Decimal:
        """核价用：读成品报废率，无效或缺失则回退 0.003（千分之3）。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_SCRAP_RATE
        return self._normalize_permille_rate(
            getattr(row, "finished_scrap_rate", None),
            DEFAULT_FINISHED_SCRAP_RATE,
        )

    def get_finished_pretax_profit_rate(self, db: Session) -> Decimal:
        """核价用：读成品税前利润率，无效或缺失则回退 0.02。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_PRETAX_PROFIT_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_pretax_profit_rate", None),
            DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
        )

    def get_base_price_processing_fee_limit(self, db: Session) -> Decimal:
        """基准价加工费上限（元/吨），即设置里保存的那个数。大于此值整批拒绝。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT
        return self._normalize_non_negative_q2(
            getattr(row, "base_price_processing_fee_limit", None),
            DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
        )

    def get_body_panel_max_thickness(self, db: Session) -> Decimal:
        """基准价参考规格：乘用车车身件料厚上限（mm）。大于此值整批拒绝，等于此值允许。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_BODY_PANEL_MAX_THICKNESS
        return self._normalize_non_negative_q2(
            getattr(row, "body_panel_max_thickness", None),
            DEFAULT_BODY_PANEL_MAX_THICKNESS,
        )

    def get_base_price_month_move_limit(self, db: Session) -> Decimal:
        """基准价导入：同一基地同一规格，单价加加工费相对上月允许的最大涨跌（元/吨）。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT
        return self._normalize_non_negative_q2(
            getattr(row, "base_price_month_move_limit", None),
            DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
        )

    def get_swing_shear_process_fee_per_ton(self, db: Session) -> Decimal:
        """核价用：摆剪件加到钢价上的元/吨，无效或缺失则回退 150。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON
        return self._normalize_non_negative_q2(
            getattr(row, "swing_shear_process_fee_per_ton", None),
            DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
        )

    @staticmethod
    def _strip_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_density(value: Any) -> Decimal:
        try:
            density = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return DEFAULT_STEEL_DENSITY
        if density <= 0:
            return DEFAULT_STEEL_DENSITY
        return quantize_money(density, Q4)

    @staticmethod
    def _normalize_loss_rate(value: Any) -> Decimal:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return DEFAULT_MATERIAL_LOSS_RATE
        if rate < 0:
            return DEFAULT_MATERIAL_LOSS_RATE
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_recovery_rate(value: Any) -> Decimal:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return DEFAULT_SCRAP_RECOVERY_RATE
        if rate <= 0 or rate > 1:
            return DEFAULT_SCRAP_RECOVERY_RATE
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_percent_rate(value: Any, default: Decimal) -> Decimal:
        """百分比费率（0~1，含 0）。"""
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default
        if rate < 0 or rate > 1:
            return default
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_permille_rate(value: Any, default: Decimal) -> Decimal:
        """千分率（≥0）。"""
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default
        if rate < 0:
            return default
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_non_negative_q2(value: Any, default: Decimal) -> Decimal:
        """非负数值，两位小数。元/吨与毫米共用。"""
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default
        if amount < 0:
            return default
        return quantize_money(amount, Q2)
