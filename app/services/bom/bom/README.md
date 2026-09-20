# 材料清单（`services/bom/bom`）

材料清单头、树节点、L0 树期、SOP 导入、工程变更种树。不是焊接费 / 采购对象那些派生切片。

没有总门面类。按职责从本包模块 import。禁止 `bom_service.py`，禁止本包 `__init__.py` 再导出。

仓储对位：`app/repositories/bom/bom/`。算法在 `period_trees.py`（改期口径只改那里）。禁止 `bom_repository.py`。

## 调谁

| 你要做什么 | 调 |
|---|---|
| 清单列表 / 创建删除 / 级联筛 / 有没有下游占用 | `BomSnapshotService` |
| 某份清单的树（平铺或树形）、手工增删节点 | `BomNodeService` |
| 当月有效树、年交集树、树根版本字 → 节点 id | `BomPeriodService` |
| 工程变更找 L0、写失效、种树、回滚删树 | `BomEngineeringService` |
| SOP Excel 导入 / 下载模板 | `BomUploadService`（`upload/`） |
| 已知节点列表上收一棵子树 | `trees.collect_subtree` |

下游（焊接拆解 / 焊接费 / 总成核价）**只问** `BomPeriodService`，不要自己 JOIN `bom_nodes` 筛树。拿到 id 后按 `source_node_id IN ids` 取派生行。

生成焊接拆解仍走 SOP 快照包（`get_by_unique_key`），和本包的树期门不是同一条路。

## 文件

| 模块 | 职责 |
|------|------|
| `snapshot.py` | 清单头 |
| `node.py` | 清单内节点 CRUD 与展示 |
| `period.py` | L0 树期对外门 |
| `engineering.py` | 工程变更对树的读写；种树规格 `BomChangePlantSpec` 从这里取 |
| `change_tree_plant/` | 种树算法。生产代码只经 `BomEngineeringService`，不要从包根 import |
| `trees.py` | `collect_subtree`（同 snapshot 节点列表、按 `parent_id`） |
| `rules/` | 解析后的树规则：一物一码、L0 序号、分总成构成。SOP 上传与工程变更共用，不是四个 Service 的杂项抽屉 |
| `upload/` | SOP 材料清单导入：编排 / 门禁 / 落树。路由仍在 `routers/bom/upload.py` |

## 仓储（`repositories/bom/bom/`）

| 类 | 职责 |
|---|---|
| `BomSnapshotRepository` | 清单头行 |
| `BomNodeRepository` | 节点行；**不含**树期过滤 |
| `BomPeriodRepository` | 取林，再套 `period_trees` |

import：`app.repositories.bom.bom.node` / `snapshot` / `period`。不要从 `repositories.bom` 包根再导出。

## 树期口径（写死）

只认 L0 树根，再收整棵子树。禁止用 L1/L2 本行生失效筛半棵树。

- 月命中 → `list_as_of_trees`
- 年交集 → `list_year_overlap_trees` / `node_ids_overlapping_year`
- 树根版本字 → `node_ids_for_l0_version` / `list_l0_versions`

`bom_version` 空字：生成拆解报业务错误，禁止回退清单头。
