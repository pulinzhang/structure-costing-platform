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

    MENU_STAMPING_UPLOAD = "menu:stamping-upload"  # 上传工艺文件
    STAMPING_UPLOAD_VIEW = "op:stamping-upload:view"  # 查看
    STAMPING_UPLOAD_UPLOAD = "op:stamping-upload:upload"  # 上传

    MENU_STAMPING_PARTS = "menu:stamping-parts"  # 零件列表
    STAMPING_PARTS_VIEW = "op:stamping-parts:view"  # 查询
    STAMPING_PARTS_UPDATE = "op:stamping-parts:update"  # 编辑工序
    STAMPING_PARTS_DELETE = "op:stamping-parts:delete"  # 删除

    MENU_STAMPING_TONNAGE = "menu:stamping-tonnage"  # 冲次费率
    STAMPING_TONNAGE_VIEW = "op:stamping-tonnage:view"  # 查询
    STAMPING_TONNAGE_CREATE = "op:stamping-tonnage:create"  # 新增
    STAMPING_TONNAGE_UPDATE = "op:stamping-tonnage:update"  # 编辑
    STAMPING_TONNAGE_DELETE = "op:stamping-tonnage:delete"  # 删除
    STAMPING_TONNAGE_COPY = "op:stamping-tonnage:copy"  # 复制年度模板

    MENU_YISHIYIYI = "menu:yishiyiyi"  # 一事一议

    MENU_THICKNESS = "menu:thickness"  # 加减价政策（厚度/宽度/其它条件）

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

    MENU_STEEL_PRICE = "menu:steel-price"  # 钢材联动价

    MENU_STEEL_PRICE_CALC = "menu:steel-price-calc"  # 钢材联动计算
    STEEL_PRICE_CALC_VIEW = "op:steel-price-calc:view"  # 查看
    STEEL_PRICE_CALC_RUN = "op:steel-price-calc:run"  # 开始计算
    STEEL_PRICE_CALC_DELETE = "op:steel-price-calc:delete"  # 删除日志

    MENU_STEEL_PRICE_LIST = "menu:steel-price-list"  # 钢材联动价格一览
    STEEL_PRICE_LIST_VIEW = "op:steel-price-list:view"  # 查询
    STEEL_PRICE_LIST_UPDATE = "op:steel-price-list:update"  # 编辑
    STEEL_PRICE_LIST_DELETE = "op:steel-price-list:delete"  # 删除
    STEEL_PRICE_LIST_APPROVE = "op:steel-price-list:approve"  # 审核通过
    STEEL_PRICE_LIST_REJECT = "op:steel-price-list:reject"  # 驳回
    STEEL_PRICE_LIST_REVERSE = "op:steel-price-list:reverse"  # 反审核
    STEEL_PRICE_LIST_EXPORT = "op:steel-price-list:export"  # 导出

    MENU_BOM = "menu:bom"  # BOM

    MENU_BOM_STRUCTURE = "menu:bom-structure"  # 产品结构
    BOM_STRUCTURE_VIEW = "op:bom-structure:view"  # 查看

    MENU_BOM_UPLOAD = "menu:bom-upload"  # 上传材料清单
    BOM_UPLOAD_VIEW = "op:bom-upload:view"  # 查看
    BOM_UPLOAD_UPLOAD = "op:bom-upload:upload"  # 上传

    MENU_COSTING = "menu:costing"  # 核价
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

