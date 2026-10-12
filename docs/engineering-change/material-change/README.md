# 材料变更 — 设计目录

> 状态：**设计定稿，业务已落地。** 前缀 `/api/engineering-change/material`。  
> 对人说 **材料变更**（对仗「设计变更」）。冲压域字段 material，对人说材料。不要另叫 grade/牌号。不要和 BOM「材料清单」混称。  
> 旧长稿已拆到本目录。入口：[工程变更地图](../README.md)、[服务包](../../../app/services/engineering_change/material_change/README.md)。  
> 网页整套测试和两本样表：[samples/](samples/README.md)。

---

## 一句话

互换性不影响时，同号从生效月切开材料。Excel 记在本通道。历史记在冲压零件上。**一个接口：** 钢材联动和零件单价都调 `list_materials_as_of`。零件明细用同一次详情里的 `material_changes`。不改 `list_with_processes`，不改零件价相等那一行。

---

## 落地顺序（一次一篇）

先读 [00-contract.md](00-contract.md)。代码按 01 → 03、04、05 做。04 只加冲压 `list_materials_as_of`，钢材 Step1 和零件价 prepare 改调它。

| 序 | 文档 | 这一刀落地什么 | 依赖 |
|----|------|----------------|------|
| 0 | [00-contract.md](00-contract.md) | 不写业务代码。判据、ADR、T13J 样例、范围 | — |
| 1 | [01-tables-resolver.md](01-tables-resolver.md) | 三张表 + 冲压零件当月材料 + 单测 | 0 |
| 2 | [02-upload-gates.md](02-upload-gates.md) | Excel、`ECM_*` 中文、MIXED 查哪、模板/异步上传 | 1 |
| 3 | [03-menu-list-rollback.md](03-menu-list-rollback.md) | 菜单路径、权限、API、整本回滚、原件 | 2 |
| 4 | [04-steel-and-part-cost.md](04-steel-and-part-cost.md) | `list_materials_as_of`：钢材与零件价共用这一个取材质接口 | 1 |
| 5 | [05-engine-display-revise.md](05-engine-display-revise.md) | 零件详情带回历史。改图把冲压历史抄到新零件 | 3 |
| — | [06-test.md](06-test.md) | 成功两本 + 负例清单（随 2–3 刀测） | 2 |

禁止把材料变更写成设计变更的一种。禁止把叠出的材料写回 `stamping_parts.material`。禁止改 `app/common`。禁止改零件价 `grade ==` 与核价引擎。

---

## 现网举例（各篇共用）

芜湖 T13J 振华 `403014115AA` / `403014116AA`。第一刀 [samples/t13j-2026-06-material-change.xlsx](samples/t13j-2026-06-material-change.xlsx) `MAT-202506` DC01→DC03、料厚 1.5→1.5。再变回去 [samples/t13j-2026-07-material-change.xlsx](samples/t13j-2026-07-material-change.xlsx) `MAT-202507` **DC03→DC01**（变更前必须是库里最新 DC03）。工艺行始终 DC01。变更后料厚相对变更前超过 20% 整本拒。门禁见 [02-upload-gates.md](02-upload-gates.md) §4.1。
