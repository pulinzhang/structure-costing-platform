# 焊接工艺拆解 — 设计说明

> **状态：已上线。** 口径以本文与代码为准。  
> **产品入口：** `#/bom-welding-process-breakdown`（生成）、`#/bom-welding-process-breakdown-list`（列表）。  
> **API：** `/api/bom/welding-process-breakdown`。  
> 切片：**`bom`**。从材料清单 `weld_info` 生成过程量；**不算钱**。  
> **生失效不落拆解表**：取期 join source `bom_nodes`（`source_node_id`）。现网主表已有基地/项目/版本。  
> **口径（写死）：** snapshot **只约束拆解生成**（SOP 那一包：`get_by_unique_key` / `version_source=snapshot`）。焊接费计算和拆解列表一样 **认树根，不认 SOP 头**。行上 `bom_version` 抄所属 L0；列表/批量/排序认树根字与投产槽 `seq_no`。  
> 硬约束：分层见 [architecture.md](../architecture.md)。Parser 只能被 Service 调用。

---

## 0. 一句话

**把焊接原文拆成「这一件有几道工艺、各多少量」，供核对和后续计费引用。**  
有原文的节点都拆（总成 + 分总成）；乘焊接单价是 [焊接费](welding-fee-design.md) 的事（按节点 `level` 落同一张表）。

| 对人说法 | 内部 |
|----------|------|
| 焊接工艺拆解 | `bom_welding_process_breakdown_node` + `_line` |
| 原文 | `weld_info` / `weld_info_raw` |
| 单件过程量 | `process_qty`（未乘装配用量） |
| 装配用量 | `assembly_qty`（BOM 节点 `qty`） |

侧栏：**焊接工程 → 焊接工艺拆解**（拆解 / 拆解列表）。

---

## 1. 和焊接费怎么分工

```text
材料清单 weld_info
        │  Parser（纯函数）
        ▼
焊接工艺拆解（有原文即拆；不算年账）
        │  范围三列从节点抄；生失效 join source_node_id → bom_nodes
        └─ 按 node.level 计费 ──►  bom_welding_fees
              ├─ level=0 ──► 财务成品账
              └─ level=1 ──► 采购应成本
```

| 模块 | 做什么 | 不做什么 |
|------|--------|----------|
| 本文 | 扫树上 **有焊接原文** 的节点，落过程量、映射标准工艺、打 rollup | 不乘单价、不按年存结果、不落生失效、不独立改期 |
| 焊接费 | 对该节点拆解行 × 年单价（`level` 抄自拆解）；入参年+基地+项目，按 L0 树根取期 | 不编工艺、不靠版本/snapshot、不再扫树认人 |

拆解 **没有计算年字段**（不是年账）。同一 `(location, vehicle_model, bom_version)` 共用一份拆解。换年只换单价表，不必为每一年再拆一份。**生失效只在 `bom_nodes` 上**，拆解用 `source_node_id` 取，见 [有效期 §6](../engineering-change/bom-process-die-effective-period-design.md)。

---

## 2. 拆谁

生成时取出该 snapshot 全部 `bom_nodes`，候选为：

```text
weld_info 非空
```

SOP / 无设变：仍扫全林。工程变更不走本页 generate：从旧树已有拆解结果抄到新树（§6.1）。**工程变更写入后**本页 generate 才拒绝；写入前保持整包。

**不按 level 过滤。** 分总成只要材料清单写了焊接列，就会落主表 + 明细。

| 树上 | 有原文时 | 无原文 |
|------|----------|--------|
| L0 供货总成 | 拆；无有效工艺则 `unparsed`/`partial`，备注计费异常 | 不落行 |
| L1 分总成（有子件） | **拆**；供核对 L0 过程量从哪来，也供将来 n=1 计费 | 不落行 |
| L1 叶子（冲压件等） | 极少；T13J 叶子焊信为 0 | 不落行 |
| L2 | 也会生成，但 `parse_status = anomaly`（末级不该有焊信） | 不落行 |

无子件的退化 L0 只要有焊信（电泳等）同样拆，并备注「供货总成无下级子件」。

---

## 3. 过程量口径

两套量不要混：

| 字段 | 含义 |
|------|------|
| `process_qty` | 做 **1 件该节点** 的工艺量，与原文数字一致 |
| `assembly_qty` | 相对父件套数（BOM `qty`） |
| `process_qty_secondary` | 辅助量（如塞焊旁的 mm）；计费时辅助量优先 |

核对 L0 是否等于下级合计时才滚乘：

```text
L0.process_qty(token)  ≟  Σ( L1.process_qty × L1.assembly_qty )
```

明细上的 `rollup_flag`：

| 标记 | 何时 |
|------|------|
| `own` | 默认；该行自己的量 |
| `rolled_in_parent` | L1 该 token 滚乘合计 **等于** L0 同名 token |
| `orphan_child` | L1 有、L0 **没有** 同名 token |

`rolled_in_parent` 只解释「已经包含在总成原文里」，**不是**「L1 不要拆」。L1 行照样落库。

紧固件类（凸焊 / 植焊 / 铆接）另做子件用量对照（`qty_check_*`），**只核对、不计费**。

---

## 4. Parser（横向工具）

`app/parsers/bom/welding_process_breakdown_parser.py`：输入一段 `weld_info`，输出工艺项 + `ok` / `partial` / `unparsed`。

- 归一化全半角冒号、黒→黑、㎡→m2 等。
- token 映射到 `WeldingStandardProcessName`（与焊接单价 `item_name` 对齐），`map_status`：`ready` / `ambiguous` / `unmapped`。
- 面积 / 电泳面积默认「电泳（盐雾试验要求≤244H）」；升档见应成本文档盐雾待拍板。
- 连续冒号（`凸焊:：2`）压成单个冒号；`电泳黑漆：0.098m2` 按电泳面积。
- `焊缝：3条（60mm）` 与 `焊缝：3条 68mm`（无括号）均拆成 CO2焊缝，计费取 mm 长度。
- `焊缝：18条 （218+30）mm`：括号内加总（248mm）作为次要过程量 / 计费长度。
- `搭铁：N个` 按植/螺柱/凸焊。

材料清单写法再变时 **改 Parser 后重跑拆解**，不要在计费模块补正则。

Router **禁止** 直接调 Parser。

---

## 5. 表

```text
bom_welding_process_breakdown_node     有焊信的一个 BOM 节点
 └── bom_welding_process_breakdown_line  该节点一种工艺一行
bom_welding_process_breakdown_generate_logs  一次「开始拆解」一条（含 processing 锁）
```

### 5.1 主表

**唯一键：** `(location, vehicle_model, bom_version, source_node_id)`  
`source_node_id` = 生成时 `bom_nodes.id`（重导材料清单后会变，须再生成）。  
**不要**在拆解表加生失效四列。UNIQUE 本来就不含它们。

| 分组 | 字段 | 说明 |
|------|------|------|
| 范围 | `location`, `vehicle_model`, `bom_version` | `location` / `vehicle_model` 从 source 节点抄。`bom_version` **抄所属 L0 树根字**（设变后是 `EC-*`，不是 snapshot 头）。生成页找包仍用 SOP 头；列表/UNIQUE 认树根 |
| 时段 | （不落表） | `source_node_id` INNER JOIN `bom_nodes` 读四列 |
| 溯源 | `snapshot_id`, `source_node_id`, `excel_row` | `source_node_id` 是取期钥匙；`snapshot_id` 不是身份 |
| 零件 | `part_number`, `level`, `parent_*`, `supply_*` | L0 的 `supply_*` 为自身 |
| 量 | `assembly_qty` | 不是焊点个数 |
| 原文 | `weld_info_raw` | |
| 解析 | `parse_status`, `process_line_count`, `qa_note` | L0 且行数=0 → 计费会失败 |
| 审核 | `audit_status` 等 | 已审禁止改、删、再生成覆盖 |

`parse_status`：`ok` / `partial` / `unparsed` / `anomaly`。

明细表也不落四列。拆解列表 **不提供** 改期。BOM L0 改期级联子树后，join 立刻看见新期，不必为改期再生成。`source_node_id` 空或节点已删：该行不参加年交集，须再生成。

### 5.2 明细

级联删除。落 `process_token`、`matched_span`、过程量 / 辅助量、标准工艺名与单位、`map_status`、`rollup_flag`、紧固件校验字段。

### 5.3 生成日志

锁范围：`location + vehicle_model + bom_version`。同一范围一条 `processing`。超过 **2 小时** 可释放。冲突 → `BusinessException` **409**。

---

## 6. 生成流程

异步：`POST /generate` 立刻返回 `task_id`。范围键 **基地 + 车型 + BOM 版本**（可选顾客名校验）。

```text
start_generate
  → processing 日志当范围锁
  → 已审行存在则拒绝（须先批量反审核）
  → 删该范围未审核旧拆解
  → 对每个有 weld_info 的节点：从该 `bom_nodes` 抄范围三列（`bom_version` 抄所属 L0 树根，不抄生失效、不抄 snapshot 头；树根空字报业务错误）→ Parser → 落主表+明细 → 紧固件校验
  → apply_rollup_flags
  → 日志终态
```

过程日志在范围段写一行中性统计：`L0 无子件且无焊信 N 件（不落拆解；有处理费须补焊信）`。不点名零件，不写成毛坯供货。

`GET /generate/prep-stats`：有无清单、有焊信节点数、已审条数、是否可点生成。

手工改明细后，同一范围 **重算** rollup 与子件校验（`recompute`），避免核对态撒谎。

### 6.1 工程变更写入后才禁止整包 generate

现网 generate 扫 **整份 snapshot**：有已审 409，无已审则删未审再全林。Parser / UNIQUE **不改**。

**工程变更写入后**才收窄本页「开始生成」：该 snapshot 一旦有已失效树根、**或** 存在生效月不是项目 SOP 开始月的树根 → 拒绝（即使没有已审）。与采购对象同一把钥匙 `snapshot_blocks_full_generate`。设变后的总成没有拆解走 [工程变更](../engineering-change/part-number-revision-design.md) 重传，本页不提供「只补该树」。工程变更写入前本页保持整包 generate。

工程变更同一事务：按新旧 BOM 节点对照，把旧树 **已有拆解结果** 抄到新树再插一套（主表身份对齐新节点；`weld_info_raw` / 解析态 / 过程量等与 **全部明细行**——可多行——从旧结果照抄）。**禁止**按新节点 `weld_info` 重新自动拆（保留手工改量）。不删旧树拆解。无旧拆解可对的新节点不插。行上 `bom_version` **抄新树根字**，不抄 snapshot 头。核价引擎缺拆解时 **仍调** 本页同进程 `generate`（找包仍用 SOP 头）；若本钥匙拦住，由引擎映射为 `EC_GATE_ENGINE_BREAKDOWN`（工程变更 §4.6 门禁之 3）——不是「引擎从不调 generate」。工程变更上传是长任务，不走本页。

---

## 7. 列表、审核、导出

| 动作 | 口径 |
|------|------|
| 列表 | 分页；可筛 level / 零件号 / 工艺行数等 |
| 改明细 | 待审；已审须先反审核 |
| 删除 / 审核 / 反审核 | **只批量、按范围**；意见 / 原因必填。删除与重生成清未审：焊接费 `source_breakdown_node_id` `RESTRICT`；仍被引用 → 「仍被焊接费引用，请先删除对应焊接费后再删」 |
| 导出 | **L0 核对表**（强制总成层；主表字段合并到明细行；不含审核列） |

列表可看 L1，导出核对表只出 L0——L1 用来对「总成量从哪来」，不是另出一张分总成工费 Excel。

旁证（evidence）：L0 ↔ L1 滚乘、L2 紧固件路径，给列表/抽屉看差异，不改计费。

权限见 [permission-design.md](../permission-design.md)（`menu/op:bom-welding-process-breakdown*`）。

---

## 8. 分层与路径

```text
Router  welding_process_breakdown.py
  → BomWeldingProcessBreakdownService     门面
       ├── generate/service · generate/log · generate/task
       ├── audit/service
       ├── export/orchestrator            L0 核对导出
       └── bom_tree · rollup · fastener_check · evidence · recompute
Parser  仅 generate / 改量映射 经 Service 调用
```

| 路径 | 角色 |
|------|------|
| `app/parsers/bom/welding_process_breakdown_parser.py` | 原文 → 工艺项 |
| `app/services/bom/welding_process_breakdown/` | 本切片 |
| `app/common/bom/welding_standard_process.py` | 标准工艺名 |
| `static/js/features/bom/welding-process-breakdown/` | 前端 |

下游：Ln 焊接费、核价引擎年度补算拆解、应成本读 L1 行。本切片 **不** 依赖 costing。

核价引擎：该 L0Scope 还没有拆解时同进程自动 `generate` 一次（门禁在 generate 内）。年交集已齐则跳过；不可整包时引擎报 `EC_GATE_ENGINE_BREAKDOWN`，见 [工程变更 §4.6](../engineering-change/part-number-revision-design.md)。

---

## 9. 做 / 不做

| 做 | 不做 |
|----|------|
| L0+L1（有原文）都拆 | 再扫树认外发件 |
| 单件过程量 + rollup 对账 | 在本模块乘焊接单价 |
| L2 误填焊信标 anomaly | 第三套拆解给委外 |
| 导出 L0 核对表 | 把拆解列表当成采购对象清单 |

---

## 10. 相关文档

| 文档 | 关系 |
|------|------|
| [welding-fee-design.md](welding-fee-design.md) | 按拆解 `level` 计费；一表 `bom_welding_fees`；按 L0 树根年交集取件 |
| [bom-process-die-effective-period-design.md](../engineering-change/bom-process-die-effective-period-design.md) | 生失效只在 `bom_nodes`；拆解用 `source_node_id` 取 |
| [assembly-costing-design.md](../costing/assembly-costing-design.md) | 成品账读焊接费 **level=0** |
| [l1-assembly-costing-design.md](../costing/l1-assembly-costing-design.md) | 应成本工艺量来自 L1 拆解行 |
| [costing-engine-design.md](../costing/costing-engine-design.md) | 年度步骤可补算拆解；引擎调 generate，门禁在 `snapshot_blocks_full_generate` |
| [part-number-revision-design.md](../engineering-change/part-number-revision-design.md) | 工程变更从旧树拆解结果抄到新树（主表+全部明细，禁止按焊信重拆）；行上 `bom_version` 抄树根 |
| [bom-procurement-objects-design.md](bom-procurement-objects-design.md) | 认人不读拆解 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-31 | 按现网补文档：有原文即拆（含分总成）、过程量与装配用量、rollup、生成/审核/导出。 |
| 2026-08-31 | 计费侧改为 `bom_welding_fees` + `level`。 |
| 2026-09-16 | 生失效不落拆解表；用 `source_node_id` join `bom_nodes` 取期。范围三列现网已有。 |
| 2026-09-16 | 设变后禁止整包 generate；工程变更插行 `bom_version` 抄 snapshot 头；引擎不得用本页补新树。 |
| 2026-09-17 | 生成闸与采购对象对齐：已失效树根或生效月不是 SOP 开始月都拒绝整包 generate。 |
| 2026-09-17 | 收口：禁止整包 generate 的钥匙在 `snapshot_blocks_full_generate`；引擎同进程调 generate，拦住则映射引擎文案。Parser 不改。 |
| 2026-09-18 | 工程变更改为从旧树拆解结果抄到新树（主表+全部明细，可多行）；禁止按新节点焊信重拆。 |
| 2026-09-20 | 焊接费对拆解主表 `RESTRICT`；批量删除 / 重生成清旧行被引用则拒绝，文案见上。 |
| 2026-09-20 | **口径写死：** snapshot 只约束拆解生成（SOP 那一包）；焊接费计算和列表一样认树根，不认 SOP 头。行上版本抄 L0；废止抄 snapshot 头。 |
