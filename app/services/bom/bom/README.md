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

## 真实例子（青岛 / T28）

数字对齐 `tests/bom/test_welding_tree_root_version.py` 和工程变更切点（新树生效月的前一月写旧树失效）。

一份清单头（SOP 快照包，三键唯一）：

| 清单头 | 值 |
|---|---|
| 基地 / 项目 / 头版本 | 青岛 / T28 / `D/09` |
| 取法 | `BomSnapshotRepository.get_by_unique_key("青岛", "T28", "D/09")` |

头上只有 `D/09`。工程变更**不另建清单头**，新树种在同一 `snapshot_id` 里。`get_by_unique_key(..., "EC-202505")` 找不到。

2025-05 切过一刀之后，林里两棵 L0（同一 excel_row、靠零件号分先后）：

| | SOP 树 | 设变树 |
|---|---|---|
| L0 零件号 | `ROOT-AA` | `ROOT-AB` |
| L0 `bom_version`（树根字） | `D/09` | `EC-202505` |
| 生效 | 2020-01 | 2025-05 |
| 失效 | 2025-04 | 空（一直有效） |
| 子件 | L1 `CHILD-A` | L1 `CHILD-B` |

工程变更：`expire_l0_tree` 把 **整棵** SOP 子树写成失效 2025-04，再 `plant_change_tree` 种 `ROOT-AB`。切点来自 `previous_month(2025, 5)`。

### 问树期门（核算 / 列表 / 焊接费）

下游只拿 id，再 `source_node_id IN ids`。总成核价当月算用月命中，年账就绪用年交集。

| 你问 | 命中 |
|---|---|
| `list_as_of_trees(..., 2025, 4)` | `ROOT-AA` + `CHILD-A` |
| `list_as_of_trees(..., 2025, 5)` | `ROOT-AB` + `CHILD-B` |
| `node_ids_overlapping_year(..., 2025)` | 两棵都在（SOP 管到 4 月，设变从 5 月，都跟 2025 有交集） |
| `node_ids_for_l0_version("EC-202505")` | 只有设变树 |
| `node_ids_for_l0_version("D/09")` | 只有 SOP 树（认 L0 字，不认清单头） |
| `list_l0_versions(...)` | `["D/09", "EC-202505"]` |

拆解行上可能仍抄着头字 `D/09`。列表删筛以树根为准：筛 `EC-202505` 只动设变那棵的派生行。VO 展示用 `map_tree_root_version_by_node_id` 盖回 `EC-202505`。

### 问 SOP 快照包（生成页）

焊接拆解 / 采购对象**生成**走清单头，不是树期门：

`get_by_unique_key(青岛, T28, D/09)` → 这一包里的**全部节点**（含 `ROOT-AB`）。种过树之后生成页会 409，补树走工程变更，不要拿 `EC-202505` 当生成键。

### 半棵树（禁止）

假使有人给 `CHILD-A` 本行写了失效 2024-12，L0 仍是 2025-04：

- 对：4 月命中 L0 `ROOT-AA`，再收子树 → `CHILD-A` 仍在
- 错：对每行 `is_in_period` → 4 月丢掉 `CHILD-A`，总成核价少件

改期口径只动 `period_trees.py`。`BomNodeRepository` 不筛树期。

### 空版本字

L0 `bom_version` 空或空白：生成拆解抛 `树根「ROOT-AA」没有版本字，禁止回退清单头`。不要改成抄清单头 `D/09`。
