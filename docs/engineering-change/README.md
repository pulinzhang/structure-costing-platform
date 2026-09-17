# 工程变更

跨切片设计（BOM / 冲压 / 核价）。有效期与核价按月已落地；工程变更入口仍是设计稿。

| 文档 | 说明 |
|------|------|
| [bom-process-die-effective-period-design.md](bom-process-die-effective-period-design.md) | 交货总成、冲压零件、模具零件：生失效 + 停整包覆盖 + 按月查看（已落地） |
| [part-number-revision-design.md](part-number-revision-design.md) | 独立切片 `engineering_change`（只调上游 Service）；封皮十列；契约 §4.6–4.7、§8–§10 |
| [t28-2025-07-import-bundle-test-design.md](t28-2025-07-import-bundle-test-design.md) | 测试：青岛 T28 · 2025-07 对照一本 / 上传五份（§14） |
| [samples/engineering-change-t13j-3086ab.xlsx](samples/engineering-change-t13j-3086ab.xlsx) | T13J 3086AA→AB 样表（封皮 + 三份日常导入模板） |
| [samples/build_t28_2025_07_import_bundles.py](samples/build_t28_2025_07_import_bundles.py) | 从库生成 T28 测试 Excel |
| [samples/t28-2025-07-import-bundle.xlsx](samples/t28-2025-07-import-bundle.xlsx) | T28 2025-07 对照样表（封皮十列五行；模具布点非门禁） |

一口价年内分段不在本目录，见 [effective-period-design.md](../costing/effective-period-design.md)。
