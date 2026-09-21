# 总成核价 · 成本还原（`restore/`）

只读装配：按已落库核价卡还原当时口径。不重算、不写库。

对外入口：`AssemblyCostRestoreService`（`service.py`）。  
HTTP：`GET /api/costing/assembly-costs/restore`（按零件号选卡）、`GET /api/costing/assembly-costs/{cost_id}/restore`。  
产物：`AssemblyCostRestoreVO`。

## 架构

组合，不继承。Service 构造 Repository，再装配协作类：

```text
AssemblyCostRestoreService
  RestoreTree(node_repo)
  RestoreLookups(stamping_repo, annual_repo)
  RestoreDocuments(upload_file_repo)
  RestoreStamping(documents)
  RestoreMaterial(tree, stamping)
  RestoreWelding(welding_repo)
  RestoreIdentity()
```

`get_restore` 编排顺序：取卡 → 快照树 → 冲压/年价批量加载 → 材料行 → 织树 → 焊接/摊入 → 恒等式 → 文件去重。

## 职责

| 模块 | 类 | 职责 |
|------|----|------|
| `service.py` | `AssemblyCostRestoreService` | 选卡（财务根 / 采购对象）、编排、填 VO |
| `tree.py` | `RestoreTree` | BOM 快照父子、缩进、分总成占位行 |
| `lookups.py` | `RestoreLookups` | 冲压核价、年价、加工/模具/检具 ID 批量查出 |
| `material.py` | `RestoreMaterial` | 材料行按 `cost_source` 分支（冲压 / 年价 / 缺价） |
| `stamping.py` | `RestoreStamping` | 冲压卡：钢价、工序、模具、断链异常、引用文件 |
| `welding.py` | `RestoreWelding` | 焊接明细、摊入费用行 |
| `identity.py` | `RestoreIdentity` | 卡上金额 vs 明细加总 |
| `documents.py` | `RestoreDocuments` | 「当时的文件」收集与去重 |
| `labels.py` | — | 展示文案、费用码、文件品类名 |
| `money.py` | — | 金额量化与比较 |

协作类之间只通过构造注入调用，不共享 `self` 方法空间。
