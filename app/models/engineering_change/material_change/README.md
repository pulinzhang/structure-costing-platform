# 材料变更 Model（`models/engineering_change/material_change/`）

| 表 | 文件 |
|---|---|
| `engineering_change_material_upload_logs` | `upload_log.py` |
| `engineering_change_material_orders` | `order.py` |
| `engineering_change_material_effect_links` | `effect_link.py` |

父包 `__init__.py` 再导出，启动建表才扫得到。见 [服务包 README](../../../services/engineering_change/material_change/README.md)。
