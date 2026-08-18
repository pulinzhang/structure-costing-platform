"""运维与教学辅助脚本包。

保留内容：
- ``windows/``：生产安装 / 启停 / Windows 服务
- ``generate_perm_codes``：从 ``catalog.json`` 生成 ``Perm`` 常量
- ``grant_all_permissions_dev``：开发环境给非管理员灌全量权限（生产默认拒绝）
- ``seed_stamping_scrap_prices``：废料价种子（前端暂无 Excel 导入，仅有录入/导出）

不放：一次性 SQLite ALTER、临时冒烟/联调脚本（新库走 ``create_all``）。

在仓库根目录执行，例如::

    python -X utf8 -m scripts.generate_perm_codes
    python -X utf8 -m scripts.grant_all_permissions_dev
    python -X utf8 -m scripts.seed_stamping_scrap_prices
"""
