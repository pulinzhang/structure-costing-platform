"""运维与教学辅助脚本包。

保留内容：
- ``windows/``：生产安装 / 启停 / Windows 服务
- ``generate_perm_codes``：从 ``catalog.json`` 生成 ``Perm`` 常量
- ``grant_all_permissions_dev``：开发环境给非管理员灌全量权限（生产默认拒绝）
- ``seed_stamping_scrap_prices``：废料价种子（前端暂无 Excel 导入，仅有录入/导出）
- ``seed_bom_annual_part_prices``：年度零件价种子（青岛 / 2025，与导入模板样例同源）
- ``upload_stamping_die``：同步上传模具布点（默认芜湖 T13J 样本；校验失败不覆盖）
- ``purge_steel_price_policies``：清空加减价政策（开发重导）
- ``purge_steel_base_prices``：清空基准价（开发重导）
- ``import_base_price_samples``：批量导入样例「发布价格」基准价
- ``import_policy_thickness_samples``：批量导入样例「厚度加减价」政策
- ``purge_bom_process_die_costing``：清空 BOM / 工艺 / 布点及下游核算（联调重导）
- ``check_route_path_params``：守卫 Router 整数路径必须 ``/{id:int}``（见 api-type-safety §6）
- ``check_model_config``：守卫 Pydantic ``model_config`` 必须 ``ConfigDict``（见 api-type-safety §7）
- ``check_unused_code``：守卫未使用函数与参数；排除路由注入、路径参数和框架回调
- ``check_explicit_any``：守卫签名和类型声明不得新增 ``Any``（存量见基线）

不放：一次性 SQLite ALTER、临时冒烟/联调脚本（新库走 ``create_all``）。

在仓库根目录执行，例如::

    python -X utf8 -m scripts.generate_perm_codes
    python -X utf8 -m scripts.grant_all_permissions_dev
    python -X utf8 -m scripts.seed_stamping_scrap_prices
    python -X utf8 -m scripts.seed_bom_annual_part_prices
    python -X utf8 -m scripts.upload_stamping_die
    python -X utf8 -m scripts.purge_bom_process_die_costing --dry-run
    python -X utf8 -m scripts.purge_bom_process_die_costing
    python -X utf8 -m scripts.check_route_path_params
    python -X utf8 -m scripts.check_model_config
    python -X utf8 -m scripts.check_unused_code
    python -X utf8 -m scripts.check_explicit_any
"""
