"""运维与教学辅助脚本包。

保留内容：
- ``windows/``：生产安装 / 启停 / Windows 服务
- ``generate_perm_codes``：从 ``catalog.json`` 生成 ``Perm`` 常量
- ``grant_all_permissions_dev``：开发环境给非管理员灌全量权限（生产默认拒绝）
- ``seed_stamping_scrap_prices``：废料价种子（五座基地；不要在只含青岛的生产库跑）
- ``seed_prod_qingdao_scrap_prices``：生产服务器灌青岛废料价（当前 ``DATABASE_URL``）
- ``seed_bom_annual_part_prices``：年度零件价种子（青岛 / 2025，与导入模板样例同源）
- ``upload_stamping_die``：同步上传模具布点（默认芜湖 T13J 样本；校验失败不覆盖）

不放：一次性 SQLite ALTER、临时冒烟/联调脚本（新库走 ``create_all``）。

在仓库根目录执行，例如::

    python -X utf8 -m scripts.generate_perm_codes
    python -X utf8 -m scripts.grant_all_permissions_dev
    python -X utf8 -m scripts.seed_stamping_scrap_prices
    python -X utf8 -m scripts.seed_prod_qingdao_scrap_prices
    python -X utf8 -m scripts.seed_bom_annual_part_prices
    python -X utf8 -m scripts.upload_stamping_die
"""
