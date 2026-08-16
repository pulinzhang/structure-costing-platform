"""运维与教学辅助脚本包。

保留内容：
- ``windows/``：生产安装 / 启停 / Windows 服务
- ``generate_perm_codes``：从 ``catalog.json`` 生成 ``Perm`` 常量
- ``seed_stamping_scrap_prices``：废料价种子（前端暂无 Excel 导入，仅有录入/导出）

在仓库根目录执行，例如::

    python -X utf8 -m scripts.generate_perm_codes
    python -X utf8 -m scripts.seed_stamping_scrap_prices
"""
