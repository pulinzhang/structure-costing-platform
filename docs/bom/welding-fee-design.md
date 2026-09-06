# 焊接费 — 设计说明

> **状态：已上线。** 表 `bom_welding_fees` + `level`；公式与层级无关。财务读 `level=0`。  
> 切片：**`bom`**。只读焊接工艺拆解与焊接单价。  
> 硬约束：分层见 [architecture.md](../architecture.md)；编排见指挥家宪法。

---

## 0. 一句话

**一张年工费账，用 `level` 区分树上哪一层。**  
该节点自己的拆解过程量 × 该年该基地焊接单价。公式与 level 无关；读者自己按层取行。

```text
bom_welding_fees.level = 拆解节点.level   // 0、1、2 … 7，整数，不写死枚举
```

现网材料清单是三级（0/1/2）。表和切片按 **任意非负整数 level** 建，以后 BOM 出现 L7 不必再开 `bom_l7_welding_fees`。

---

## 1. 为什么重构

| 现网 | 问题 |
|------|------|
| 表 / 包 / API / 权限都叫 `l0` | 加分总成就要复制整切片 |
| 计算写死 `level==0` | L1、L2、将来 L7 进不来 |
| 金额字段 `total_l0_welding_fee` | 名字绑死总成 |

**拍板：** 一个切片、三张表、一行一个拆解节点，**用 `level` 过滤**，不要 `bom_l0_*` / `bom_l1_*` 并列。

---

## 2. 计谁（跟拆解走）

拆解已经是「有 `weld_info` 就落节点」，并带 `level`。焊接费 **不再自己认人**：

```text
对该范围每一个拆解节点（可选入参 levels 过滤）：
  抄 node.level
  用该节点自己的明细 × 年单价
  写成 bom_welding_fees 一行
```

| level | 树上常见是谁 | 业务谁读 |
|-------|----------------|----------|
| 0 | 供货总成（含退化电泳板） | 财务成品月总账 |
| 1 | 分总成（有子件、有焊信） | 采购应成本工艺费 |
| 2 | 仅当 L2 **误填/真有** 焊信 | 核对；默认列表可藏 |
| 3…n | 将来更深的层 | 同一张表，同一公式 |

**不**在焊接费里写死「L2 永不计费」。没有拆解行就没有焊接费行。L1 无焊信的冲压叶子拆解本来就不会生成，这里也没有行。

退化供货件仍是 **level=0**（树上在总成位）。

---

## 3. 共用公式（与 level 无关）

对每一个拆解节点：

```text
对每一条该节点自己的拆解明细：
  标准工艺名未就绪 → unmapped，本行不计费
  价表无该标准工艺名 → missing_price，本行不计费
  否则：
    billing_qty = 辅助量优先，否则过程量；再换算到单价单位
    line_fee    = billing_qty × unit_price

total_welding_fee = Σ 已匹配行的 line_fee
final_welding_fee = total_welding_fee + other_fee   // other 空当 0
```

- 单价：`bom_welding_unit_price`（`location + year + item_name`）。
- 计费用量：`app/common/bom/welding_billing_qty.py`。**不乘装配用量**。
- 结果 **没有 `month`**（现网）。单价分段后再加月，见 [effective-period-design.md](../costing/effective-period-design.md)。
- `calc_status`：`ok` / `partial` / `failed`（规则与现网 L0 相同）。

---

## 4. 防双计

每一行只吃 **该节点自己的** 拆解行，不把子孙明细加进父行金额。

| 规则 | 说明 |
|------|------|
| 父层不累加子层行 | L0 行 ≠ Σ L1 焊接费 |
| 子层不引用父层合计 | L1 不认 L0 原文 |
| 下游不要加总应付 | 财务只读 `level=0`；采购应成本读 `level=1`（退化特殊工艺仍可读 level=0 那一行） |

level=1 **不是** 把 level=0 拆开，而是给该分总成自己开工费卡。

---

## 5. 谁读哪一层

```text
level=0 ──► 成品月核价 ④ welding_amount / ⑤ other_fee
level=1 ──► 采购应成本 process_fee
```

| 账 | 读 |
|----|-----|
| 财务成品月总账 | **`level = 0`** 的 `final_welding_fee` / `other_fee` |
| 核价引擎补算 | 该范围缺 **level=0** 行则补算（可只跑 `levels=[0]`，以免财务任务写出未审的 L1） |
| 采购应成本 | **`level = 1`**；不要在 costing 里再乘一遍单价 |

引擎默认 **不要** 一次把 L1/L2 都写成财务账的输入。补算入参显式带 `levels`。

---

## 6. 目标表（重构后）

```text
bom_welding_fees                 1 个拆解节点 × 年 × 范围
 └── bom_welding_fee_items       该节点工艺 × 单价
bom_welding_fee_calc_logs        一次「开始计算」一条（含 processing 锁）
```

**唯一键：** `(year, location, vehicle_model, bom_version, source_breakdown_node_id)`  
`source_breakdown_node_id` 已能区分同号多树。`level` **冗余**，供筛选和索引，不进唯一键（同一拆解节点只有一个 level）。

建议索引：`(year, location, vehicle_model, bom_version, level)`。

### 6.1 主表 `bom_welding_fees`

| 分组 | 字段 | 说明 |
|------|------|------|
| 范围 | `year`, `location`, `vehicle_model`, `bom_version` | |
| **层级** | **`level`** | `SmallInteger`，**抄拆解**，≥0；禁止业务代码写死只允许 0/1 |
| 零件 | `part_number`, `part_name`, `customer_name` | 来自拆解节点 |
| 原文 | `weld_info_raw` | 计算快照 |
| 计数 | `process_line_count` / `matched_line_count` / `missing_price_count` | |
| 金额 | `total_welding_fee` | 系统计算（现网 `total_l0_welding_fee`） |
| | `other_fee` | 手填，可正可负；重算保留 |
| | `final_welding_fee` | 确认单价（现网 `final_l0_welding_fee`） |
| 状态 / 审核 | `calc_*`、`audit_*` | 与现网同构 |

明细、日志形态与现网一致；日志锁范围仍是 **年 + 基地 + 车型 + 版本**（一次计算可覆盖多层，不必按 level 分锁）。已审 **按行** 跳过：L0 已审不影响同范围 L1 覆盖。

### 6.2 计算入参

```text
year, location, vehicle_model, bom_version
levels: list[int] | 省略
```

- 省略 `levels`：该范围拆解里 **出现过的所有 level** 都算。
- 传入如 `[0]`：只算总成（财务补算、现网行为）。
- 传入如 `[1]`：只算分总成。
- 出现未在列表里的更深 level（如 7）：只要拆解有节点且未过滤掉，就会落行。

前置拒绝：无该基地年单价；过滤后 **零个** 拆解节点。

`GET /calc/ready`：按 level 给出节点数 / 工艺行 / 零工艺数，不要只报 L0。

---

## 7. 产品与 API（目标）

一个入口，用 level 筛，不要「成品焊接费」「分总成焊接费」两套菜单。

| 现网 | 目标 |
|------|------|
| `#/bom-l0-welding-fee-calc` | `#/bom-welding-fee-calc` |
| `#/bom-l0-welding-fee-list` | `#/bom-welding-fee-list` |
| `/api/bom/l0-welding-fees` | `/api/bom/welding-fees` |
| `menu/op:bom-l0-welding-fee-*` | `menu/op:bom-welding-fee-*` |
| 侧栏「成品焊接费」 | 「焊接费」（列表默认可看全部层级） |

批量删除 / 审核 / 反审核：范围仍是年 + 基地 + 车型 + 版本；**可加可选 `level`**，不传则该范围全部未审行。意见 / 原因必填。

列表、导出与材料清单同一套行序：``level → sort_no（缺则拆解 excel_row）→ id``。列表默认筛 **L0+L1**（`levels=0,1`）；也可单选 L0 / L1 / L2，或选「全部」不过滤层级。导出跟列表筛选。成品核价套表里的焊接费页仍只嵌 `level=0`。

---

## 8. 代码路径（目标，未实施）

```text
app/routers/bom/welding_fee.py
app/services/bom/welding_fee/          含 calc/orchestrator
app/models/bom/welding_fee.py
app/models/bom/welding_fee_item.py
app/models/bom/welding_fee_calc_log.py
app/repositories/bom/welding_fee_repository.py
static/js/features/bom/welding-fee/{calc,list}/
```

指挥家：`prepare`（单价 + 按 levels 过滤拆解）→ `engine`（逐节点套 §3）→ `persist`。  
单件公式从现网 `l0_fee.py` 改名即可，不要按 level 分支公式。

下游 costing：**只读** `final_welding_fee` where `level=0`。bom **不** 依赖 costing。

---

## 9. 从现网迁过去（实施时，现不改库）

| 现网 | 目标 |
|------|------|
| `bom_l0_welding_fees` | `bom_welding_fees`，现有行 `level=0` |
| `bom_l0_welding_fee_items` | `bom_welding_fee_items` |
| `bom_l0_welding_fee_calc_logs` | `bom_welding_fee_calc_logs` |
| `total_l0_welding_fee` / `final_l0_welding_fee` | `total_welding_fee` / `final_welding_fee` |
| 计算过滤 `level==0` | `levels` 入参，财务默认 `[0]` |

一次迁移，**不双写**。成品核价、引擎阶段名 `annual_l0_welding_fee` 改为读新表 `level=0`（阶段 id 可随后改 `annual_welding_fee`）。旧 URL / 旧权限码实施时做兼容或一次性替换（权限树见 [permission-design.md](../permission-design.md)）。

---

## 10. 做 / 不做

| 做 | 不做 |
|----|------|
| 一表 + `level`，公式共用 | `bom_l1_welding_fees` 第二套切片 |
| level 用整数，不 enumerated 死 0/1/2 | 为 L7 再开表 |
| 财务读 0、采购读 1 | 把子层金额加进父层 |
| 有拆解才有焊接费行 | 在本切片扫 BOM 认外发 |
| 现网一年一次 | 本期改月（另文） |

---

## 11. 相关文档

| 文档 | 关系 |
|------|------|
| [welding-process-breakdown-design.md](welding-process-breakdown-design.md) | `level` 与过程量的上游 |
| [l0-assembly-costing-design.md](../costing/l0-assembly-costing-design.md) | 成品账只读 **level=0**（迁表后字段名见 §9） |
| [l1-assembly-costing-design.md](../costing/l1-assembly-costing-design.md) | 应成本工艺费读 **level=1** |
| [costing-engine-design.md](../costing/costing-engine-design.md) | 补算默认 `levels=[0]` |
| [effective-period-design.md](../costing/effective-period-design.md) | 将来加 `month` 时表名跟本文 |
| `app/services/bom/welding_fee/` | 现网实现 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-31 | 按现网补 n=0。 |
| 2026-08-31 | 收口层级 n；文件改为 `welding-fee-design.md`。 |
| 2026-08-31 | **重构设计：** `bom_welding_fees` + `level`；一张表覆盖 L0/L1/L2/…；代码未动。 |
| 2026-08-31 | **已上线：** 三表改名 + `level`；切片 `app/services/bom/welding_fee/`；引擎补算 `levels=[0]`。 |
