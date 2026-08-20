"""权限码常量：与 catalog.json 一一对应。

路由 / Service 只引用 Perm.*，禁止散落字面量。
启动时由 catalog.assert_codes_synced() 校验双向一致。
"""

from __future__ import annotations

from typing import Iterator


class Perm:
    """权限码常量（值 = catalog.json 中的 code）。"""

    MENU_DASHBOARD = "menu:dashboard"  # 仪表盘
    DASHBOARD_VIEW = "op:dashboard:view"  # 查看

    MENU_STAMPING = "menu:stamping"  # 冲压工程

    MENU_STAMPING_PROCESS = "menu:stamping-process"  # 冲压工艺

    MENU_STAMPING_UPLOAD = "menu:stamping-upload"  # 上传工艺文件
    STAMPING_UPLOAD_VIEW = "op:stamping-upload:view"  # 查看
    STAMPING_UPLOAD_UPLOAD = "op:stamping-upload:upload"  # 上传

    MENU_STAMPING_PARTS = "menu:stamping-parts"  # 冲压零件列表
    STAMPING_PARTS_VIEW = "op:stamping-parts:view"  # 查询
    STAMPING_PARTS_UPDATE = "op:stamping-parts:update"  # 编辑工序
    STAMPING_PARTS_DELETE = "op:stamping-parts:delete"  # 删除
    STAMPING_PARTS_EXPORT = "op:stamping-parts:export"  # 导出

    MENU_STAMPING_STROKE_UNIT_PRICE = "menu:stamping-stroke-unit-price"  # 冲次单价

    MENU_STAMPING_TONNAGE_UPLOAD = "menu:stamping-tonnage-upload"  # 上传
    STAMPING_TONNAGE_UPLOAD_VIEW = "op:stamping-tonnage-upload:view"  # 查看
    STAMPING_TONNAGE_UPLOAD_UPLOAD = "op:stamping-tonnage-upload:upload"  # 上传

    MENU_STAMPING_TONNAGE = "menu:stamping-tonnage"  # 冲次单价列表
    STAMPING_TONNAGE_VIEW = "op:stamping-tonnage:view"  # 查询
    STAMPING_TONNAGE_CREATE = "op:stamping-tonnage:create"  # 新增
    STAMPING_TONNAGE_UPDATE = "op:stamping-tonnage:update"  # 编辑
    STAMPING_TONNAGE_DELETE = "op:stamping-tonnage:delete"  # 删除
    STAMPING_TONNAGE_APPROVE = "op:stamping-tonnage:approve"  # 审核通过
    STAMPING_TONNAGE_REVERSE = "op:stamping-tonnage:reverse"  # 反审核
    STAMPING_TONNAGE_EXPORT = "op:stamping-tonnage:export"  # 导出

    MENU_STAMPING_PROCESSING_FEE = "menu:stamping-processing-fee"  # 冲压加工费

    MENU_STAMPING_PROCESS_FEE_CALC = "menu:stamping-process-fee-calc"  # 冲压加工费计算
    STAMPING_PROCESS_FEE_CALC_VIEW = "op:stamping-process-fee-calc:view"  # 查看
    STAMPING_PROCESS_FEE_CALC_RUN = "op:stamping-process-fee-calc:run"  # 计算
    STAMPING_PROCESS_FEE_CALC_DELETE = "op:stamping-process-fee-calc:delete"  # 删除日志

    MENU_STAMPING_PROCESS_FEE = "menu:stamping-process-fee"  # 冲压加工费列表
    STAMPING_PROCESS_FEE_VIEW = "op:stamping-process-fee:view"  # 查询
    STAMPING_PROCESS_FEE_UPDATE = "op:stamping-process-fee:update"  # 编辑其它费用 / 确认单价
    STAMPING_PROCESS_FEE_DELETE = "op:stamping-process-fee:delete"  # 删除
    STAMPING_PROCESS_FEE_APPROVE = "op:stamping-process-fee:approve"  # 审核通过
    STAMPING_PROCESS_FEE_REVERSE = "op:stamping-process-fee:reverse"  # 反审核
    STAMPING_PROCESS_FEE_EXPORT = "op:stamping-process-fee:export"  # 导出

    MENU_YISHIYIYI = "menu:yishiyiyi"  # 一事一议

    MENU_THICKNESS = "menu:thickness"  # 加减价政策

    MENU_STEEL_PRICE_POLICY_UPLOAD = "menu:steel-price-policy-upload"  # 上传
    STEEL_PRICE_POLICY_UPLOAD_VIEW = "op:steel-price-policy-upload:view"  # 查看
    STEEL_PRICE_POLICY_UPLOAD_UPLOAD = "op:steel-price-policy-upload:upload"  # 导入

    MENU_STEEL_PRICE_POLICY_DOWNLOAD = "menu:steel-price-policy-download"  # 加减价政策列表
    STEEL_PRICE_POLICY_DOWNLOAD_VIEW = "op:steel-price-policy-download:view"  # 预览
    STEEL_PRICE_POLICY_DOWNLOAD_EXPORT = "op:steel-price-policy-download:export"  # 导出
    STEEL_PRICE_POLICY_DOWNLOAD_DELETE = "op:steel-price-policy-download:delete"  # 批量删除

    MENU_BASE_PRICE = "menu:base-price"  # 基准价格

    MENU_BASE_PRICE_UPLOAD = "menu:base-price-upload"  # 上传
    BASE_PRICE_UPLOAD_VIEW = "op:base-price-upload:view"  # 查看
    BASE_PRICE_UPLOAD_UPLOAD = "op:base-price-upload:upload"  # 导入

    MENU_BASE_PRICE_DOWNLOAD = "menu:base-price-download"  # 基准价格列表
    BASE_PRICE_DOWNLOAD_VIEW = "op:base-price-download:view"  # 预览
    BASE_PRICE_DOWNLOAD_EXPORT = "op:base-price-download:export"  # 导出
    BASE_PRICE_DOWNLOAD_DELETE = "op:base-price-download:delete"  # 批量删除

    MENU_WINNING_THICKNESS_DOWNLOAD = "menu:winning-thickness-download"  # 中标钢厂厚度价格一览表
    WINNING_THICKNESS_DOWNLOAD_VIEW = "op:winning-thickness-download:view"  # 预览
    WINNING_THICKNESS_DOWNLOAD_EXPORT = "op:winning-thickness-download:export"  # 导出

    MENU_SCRAP_PRICE = "menu:scrap-price"  # 废料月度销售价
    SCRAP_PRICE_VIEW = "op:scrap-price:view"  # 查询
    SCRAP_PRICE_CREATE = "op:scrap-price:create"  # 新增
    SCRAP_PRICE_UPDATE = "op:scrap-price:update"  # 编辑
    SCRAP_PRICE_DELETE = "op:scrap-price:delete"  # 删除
    SCRAP_PRICE_COPY = "op:scrap-price:copy"  # 复制月度模板
    SCRAP_PRICE_EXPORT = "op:scrap-price:export"  # 导出

    MENU_BOM = "menu:bom"  # 焊接工程（技术码仍为 bom）

    MENU_BOM_MATERIAL_LIST = "menu:bom-material-list"  # 材料清单

    MENU_BOM_UPLOAD = "menu:bom-upload"  # 上传材料清单
    BOM_UPLOAD_VIEW = "op:bom-upload:view"  # 查看
    BOM_UPLOAD_UPLOAD = "op:bom-upload:upload"  # 上传

    MENU_BOM_MATERIAL = "menu:bom-material"  # 材料清单列表
    BOM_MATERIAL_VIEW = "op:bom-material:view"  # 查看
    BOM_MATERIAL_DELETE = "op:bom-material:delete"  # 删除

    MENU_BOM_STRUCTURE = "menu:bom-structure"  # 产品结构
    BOM_STRUCTURE_VIEW = "op:bom-structure:view"  # 查看

    MENU_BOM_WELDING_UNIT_PRICE_GROUP = "menu:bom-welding-unit-price-group"  # 焊接单价

    MENU_BOM_WELDING_UNIT_PRICE_UPLOAD = "menu:bom-welding-unit-price-upload"  # 上传
    BOM_WELDING_UNIT_PRICE_UPLOAD_VIEW = "op:bom-welding-unit-price-upload:view"  # 查看
    BOM_WELDING_UNIT_PRICE_UPLOAD_UPLOAD = "op:bom-welding-unit-price-upload:upload"  # 上传

    MENU_BOM_WELDING_UNIT_PRICE = "menu:bom-welding-unit-price"  # 焊接单价列表
    BOM_WELDING_UNIT_PRICE_VIEW = "op:bom-welding-unit-price:view"  # 查询
    BOM_WELDING_UNIT_PRICE_CREATE = "op:bom-welding-unit-price:create"  # 新增
    BOM_WELDING_UNIT_PRICE_UPDATE = "op:bom-welding-unit-price:update"  # 编辑
    BOM_WELDING_UNIT_PRICE_DELETE = "op:bom-welding-unit-price:delete"  # 删除
    BOM_WELDING_UNIT_PRICE_APPROVE = "op:bom-welding-unit-price:approve"  # 审核通过
    BOM_WELDING_UNIT_PRICE_REVERSE = "op:bom-welding-unit-price:reverse"  # 反审核
    BOM_WELDING_UNIT_PRICE_EXPORT = "op:bom-welding-unit-price:export"  # 导出

    MENU_BOM_ANNUAL_PART_PRICE_GROUP = "menu:bom-annual-part-price-group"  # 年度零件价

    MENU_BOM_ANNUAL_PART_PRICE_UPLOAD = "menu:bom-annual-part-price-upload"  # 上传
    BOM_ANNUAL_PART_PRICE_UPLOAD_VIEW = "op:bom-annual-part-price-upload:view"  # 查看
    BOM_ANNUAL_PART_PRICE_UPLOAD_UPLOAD = "op:bom-annual-part-price-upload:upload"  # 上传

    MENU_BOM_ANNUAL_PART_PRICE = "menu:bom-annual-part-price"  # 年度零件价列表
    BOM_ANNUAL_PART_PRICE_VIEW = "op:bom-annual-part-price:view"  # 查询
    BOM_ANNUAL_PART_PRICE_CREATE = "op:bom-annual-part-price:create"  # 新增
    BOM_ANNUAL_PART_PRICE_UPDATE = "op:bom-annual-part-price:update"  # 编辑
    BOM_ANNUAL_PART_PRICE_DELETE = "op:bom-annual-part-price:delete"  # 删除
    BOM_ANNUAL_PART_PRICE_APPROVE = "op:bom-annual-part-price:approve"  # 审核通过
    BOM_ANNUAL_PART_PRICE_REVERSE = "op:bom-annual-part-price:reverse"  # 反审核
    BOM_ANNUAL_PART_PRICE_EXPORT = "op:bom-annual-part-price:export"  # 导出

    MENU_BOM_PACKAGING_TRANSPORT_FEE_GROUP = "menu:bom-packaging-transport-fee-group"  # 包装运输费

    MENU_BOM_PACKAGING_TRANSPORT_FEE_UPLOAD = "menu:bom-packaging-transport-fee-upload"  # 上传
    BOM_PACKAGING_TRANSPORT_FEE_UPLOAD_VIEW = "op:bom-packaging-transport-fee-upload:view"  # 查看
    BOM_PACKAGING_TRANSPORT_FEE_UPLOAD_UPLOAD = "op:bom-packaging-transport-fee-upload:upload"  # 上传

    MENU_BOM_PACKAGING_TRANSPORT_FEE = "menu:bom-packaging-transport-fee"  # 包装运输费列表
    BOM_PACKAGING_TRANSPORT_FEE_VIEW = "op:bom-packaging-transport-fee:view"  # 查询
    BOM_PACKAGING_TRANSPORT_FEE_CREATE = "op:bom-packaging-transport-fee:create"  # 新增
    BOM_PACKAGING_TRANSPORT_FEE_UPDATE = "op:bom-packaging-transport-fee:update"  # 编辑
    BOM_PACKAGING_TRANSPORT_FEE_DELETE = "op:bom-packaging-transport-fee:delete"  # 删除
    BOM_PACKAGING_TRANSPORT_FEE_APPROVE = "op:bom-packaging-transport-fee:approve"  # 审核通过
    BOM_PACKAGING_TRANSPORT_FEE_REVERSE = "op:bom-packaging-transport-fee:reverse"  # 反审核
    BOM_PACKAGING_TRANSPORT_FEE_EXPORT = "op:bom-packaging-transport-fee:export"  # 导出

    MENU_BOM_WELDING_PROCESS_BREAKDOWN_GROUP = "menu:bom-welding-process-breakdown-group"  # 焊接工艺拆解

    MENU_BOM_WELDING_PROCESS_BREAKDOWN = "menu:bom-welding-process-breakdown"  # 拆解
    BOM_WELDING_PROCESS_BREAKDOWN_GENERATE = "op:bom-welding-process-breakdown:generate"  # 从BOM生成
    BOM_WELDING_PROCESS_BREAKDOWN_DELETE_LOG = "op:bom-welding-process-breakdown:delete-log"  # 删除拆解日志

    MENU_BOM_WELDING_PROCESS_BREAKDOWN_LIST = "menu:bom-welding-process-breakdown-list"  # 拆解列表
    BOM_WELDING_PROCESS_BREAKDOWN_VIEW = "op:bom-welding-process-breakdown:view"  # 查询
    BOM_WELDING_PROCESS_BREAKDOWN_SAVE_LINES = "op:bom-welding-process-breakdown:save-lines"  # 编辑明细
    BOM_WELDING_PROCESS_BREAKDOWN_DELETE = "op:bom-welding-process-breakdown:delete"  # 删除
    BOM_WELDING_PROCESS_BREAKDOWN_APPROVE = "op:bom-welding-process-breakdown:approve"  # 审核通过
    BOM_WELDING_PROCESS_BREAKDOWN_REVERSE = "op:bom-welding-process-breakdown:reverse"  # 反审核
    BOM_WELDING_PROCESS_BREAKDOWN_EXPORT = "op:bom-welding-process-breakdown:export"  # 导出L0核对

    MENU_BOM_L0_WELDING_FEE_GROUP = "menu:bom-l0-welding-fee-group"  # 成品焊接费

    MENU_BOM_L0_WELDING_FEE_CALC = "menu:bom-l0-welding-fee-calc"  # 成品焊接费计算
    BOM_L0_WELDING_FEE_CALC_VIEW = "op:bom-l0-welding-fee-calc:view"  # 查看
    BOM_L0_WELDING_FEE_CALC_RUN = "op:bom-l0-welding-fee-calc:run"  # 计算
    BOM_L0_WELDING_FEE_CALC_DELETE = "op:bom-l0-welding-fee-calc:delete"  # 删除计算日志

    MENU_BOM_L0_WELDING_FEE_LIST = "menu:bom-l0-welding-fee-list"  # 成品焊接费列表
    BOM_L0_WELDING_FEE_LIST_VIEW = "op:bom-l0-welding-fee-list:view"  # 查询
    BOM_L0_WELDING_FEE_LIST_UPDATE = "op:bom-l0-welding-fee-list:update"  # 编辑其它费用 / 确认单价
    BOM_L0_WELDING_FEE_LIST_DELETE = "op:bom-l0-welding-fee-list:delete"  # 删除
    BOM_L0_WELDING_FEE_LIST_APPROVE = "op:bom-l0-welding-fee-list:approve"  # 审核通过
    BOM_L0_WELDING_FEE_LIST_REVERSE = "op:bom-l0-welding-fee-list:reverse"  # 反审核
    BOM_L0_WELDING_FEE_LIST_EXPORT = "op:bom-l0-welding-fee-list:export"  # 导出

    MENU_COSTING = "menu:costing"  # 核价

    MENU_STEEL_PRICE = "menu:steel-price"  # 冲压钢材联动价

    MENU_STEEL_PRICE_CALC = "menu:steel-price-calc"  # 冲压钢材联动计算
    STEEL_PRICE_CALC_VIEW = "op:steel-price-calc:view"  # 查看
    STEEL_PRICE_CALC_RUN = "op:steel-price-calc:run"  # 开始计算
    STEEL_PRICE_CALC_DELETE = "op:steel-price-calc:delete"  # 删除日志

    MENU_STEEL_PRICE_LIST = "menu:steel-price-list"  # 冲压钢材联动价一览
    STEEL_PRICE_LIST_VIEW = "op:steel-price-list:view"  # 查询
    STEEL_PRICE_LIST_UPDATE = "op:steel-price-list:update"  # 编辑
    STEEL_PRICE_LIST_DELETE = "op:steel-price-list:delete"  # 删除
    STEEL_PRICE_LIST_APPROVE = "op:steel-price-list:approve"  # 审核通过
    STEEL_PRICE_LIST_REJECT = "op:steel-price-list:reject"  # 驳回
    STEEL_PRICE_LIST_REVERSE = "op:steel-price-list:reverse"  # 反审核
    STEEL_PRICE_LIST_EXPORT = "op:steel-price-list:export"  # 导出

    MENU_STAMPING_PART_COST_GROUP = "menu:stamping-part-cost-group"  # 冲压零件价格核算

    MENU_STAMPING_PART_COST_CALC = "menu:stamping-part-cost-calc"  # 冲压零件价格计算
    STAMPING_PART_COST_CALC_VIEW = "op:stamping-part-cost-calc:view"  # 查看
    STAMPING_PART_COST_CALC_RUN = "op:stamping-part-cost-calc:run"  # 计算
    STAMPING_PART_COST_CALC_DELETE = "op:stamping-part-cost-calc:delete"  # 删除日志

    MENU_STAMPING_PART_COST = "menu:stamping-part-cost"  # 冲压零件价格一览
    STAMPING_PART_COST_VIEW = "op:stamping-part-cost:view"  # 查询
    STAMPING_PART_COST_UPDATE = "op:stamping-part-cost:update"  # 失败手工改价
    STAMPING_PART_COST_DELETE = "op:stamping-part-cost:delete"  # 删除
    STAMPING_PART_COST_APPROVE = "op:stamping-part-cost:approve"  # 审核通过
    STAMPING_PART_COST_REVERSE = "op:stamping-part-cost:reverse"  # 反审核
    STAMPING_PART_COST_EXPORT = "op:stamping-part-cost:export"  # 导出核价结果

    MENU_COSTING_ENGINE = "menu:costing-engine"  # 自动核价引擎
    COSTING_VIEW = "op:costing:view"  # 查看

    MENU_QUOTATION = "menu:quotation"  # 报价
    QUOTATION_VIEW = "op:quotation:view"  # 查看

    MENU_SETTINGS = "menu:settings"  # 设置

    MENU_SETTINGS_PROFILE = "menu:settings-profile"  # 个人资料
    SETTINGS_PROFILE_VIEW = "op:settings-profile:view"  # 查看
    SETTINGS_PROFILE_UPDATE = "op:settings-profile:update"  # 改资料/头像
    SETTINGS_PROFILE_PASSWORD = "op:settings-profile:password"  # 修改密码

    MENU_SETTINGS_SYSTEM = "menu:settings-system"  # 系统设置
    SETTINGS_SYSTEM_VIEW = "op:settings-system:view"  # 查看
    SETTINGS_SYSTEM_UPDATE = "op:settings-system:update"  # 保存设置

    MENU_SETTINGS_USERS = "menu:settings-users"  # 用户管理
    SETTINGS_USERS_VIEW = "op:settings-users:view"  # 查询
    SETTINGS_USERS_CREATE = "op:settings-users:create"  # 新增
    SETTINGS_USERS_UPDATE = "op:settings-users:update"  # 编辑
    SETTINGS_USERS_PASSWORD = "op:settings-users:password"  # 重置密码
    SETTINGS_USERS_DELETE = "op:settings-users:delete"  # 删除
    SETTINGS_USERS_GRANT = "op:settings-users:grant"  # 授权

    MENU_SETTINGS_LOGS = "menu:settings-logs"  # 操作日志
    SETTINGS_LOGS_VIEW = "op:settings-logs:view"  # 查看
    SETTINGS_LOGS_EXPORT = "op:settings-logs:export"  # 导出


def iter_perm_codes() -> Iterator[str]:
    """遍历 Perm 上全部权限码字符串。"""
    for name, value in vars(Perm).items():
        if name.startswith("_") or not isinstance(value, str):
            continue
        yield value


def get_perm_code_map() -> dict[str, str]:
    """常量名 → code。"""
    return {
        name: value
        for name, value in vars(Perm).items()
        if not name.startswith("_") and isinstance(value, str)
    }

