# 冲压年度模具费

> **状态：已落地。**

---

## 0. 一句话

按 **年 + 采购基地 + 项目**，用已入库布点各序重量和模具单价，算出 **系统模具费**；主表再加 **调整金额**，得到 **最终模具费**。算不出或系统费为 0 的不落库。只算模具。本期不进零件价、不进核价引擎。

---

## 1. 范围

| 做 | 不做 |
|---|---|
| 异步计算；锁 `year` + `location` + `vehicle_model` | 读检具、结果出现检具列 |
| 零件结果 + 各序子表 | 改布点、改模具单价；再解析布点 Excel |
| 列表 / 改调整金额 / 单条或范围删未审核 / 审核 / 反审核 / 导出 | 手工新增行；系统模具费 ≤ 0 仍入库；最终模具费 < 0；金额用 `float` |
| 计算日志 processing / success / failed | 满寿、产量累计；铸造模不单列单价档；上传结果 Excel；进零件价 / 核价引擎补算 |

计算必填 `year`、`location`、`vehicle_model`（`normalize_vehicle_model`）。一次只算一个项目。供应商、版本为**附加筛**（可空=该项目全部身份）：共模重量仍按该项目**全部布点 `id` 升序**扫描继承；只删除并重写匹配身份的结果行。计算锁仍是 `year` + `location` + `vehicle_model`（不把供应商/版本写入锁）。入队前已审核 409 只看**本次落库身份**下是否已有已审核行。

**年：** 计算页手填（建议默认当年，范围 2000–2100），不依赖「已经算过才有年」。模具单价没有年，取当前生效档；计算年只表示摊进哪一年的台账。

**列表 / 导出：** 必须先选 **年 + 基地 + 项目** 才请求、才出数（与布点清单相同）。未选齐不打接口。附加筛：供应商、版本、零件号、审核状态、`only_zero`（最终模具费为 0）。列表与导出展示快照的供应商、版本；导出筛选栏与文件名可带当前供应商/版本。

**列表 / 导出排序**（已落库件跟布点行序，不按零件号）：

```text
location ASC, vehicle_model ASC, id ASC
```

布点 Excel 按行落入 `stamping_die_parts`，`id` 升序即导入行序。计算按该顺序扫件、只写入能算出且系统费 > 0 的件，因此结果 `id` 升序 = **这些件在布点里的相对顺序**。跳过的件不出现（行数可以少于布点/原始 Excel），**不保证与 Excel 逐行一一对应**。禁止 `part_number` 排序。各序按 `process_order`。

---

## 2. 公式

单价 **万元/吨**、分摊 **万台**；结果 **元/件**。`万元 ÷ 万台 = 元/件`。

**金额与物理量：全程 `Decimal`，禁止 `float`。** 含单价、分摊万台、重量、`alloc_ratio`、各序/系统/调整/最终费用。Model 用 `Numeric` + `Mapped[Decimal]`；DTO / VO 字段 `Decimal`；JSON 入参 `mode="before"` 经 `Decimal(str(value))` 再量化（禁止 JSON number 当 `float` 参与运算）；计算与比较只用 `Decimal`。单价/费用/重量 JSON 用 `Q4` 四位字符串。**分摊万台为正整数**（`Q0`，JSON `"10"`），录入拒绝小数；展示与导出不要写成 `10.0000`。VO / Excel 用 `format_money` 输出固定小数位**字符串**，禁止 `float(x)`、`round(float(...))`。前端展示用接口字符串 + `fmtNum`，禁止 `parseFloat` 后再加减出金额。对齐 `app/common/money.py` 与类型安全「Money」规则。

**取价：** 零件 `production_mode` 含「级进模」→ `progressive_die_unit_price`；否则 → `steel_plate_unit_price`（含铸造模）。不看 `die_type` 判断级进。

**可算序：** 有效重量 > 0，且算出的 `line_die_fee > 0`。无有效重量或算出为 0 的序不写子表。

**有效重量：**

1. 本行 `estimated_weight_t` 有值且 > 0 → 用本行（自有）。
2. 否则若本序可继承共模重量 → 用 **上一件（布点 `id` 升序的前一件）** 同工序已解析重量（优先 `process_seq`，否则 `process_order`）。上一件该序必须同时有 **真实长、宽、高**（均有值且 > 0）。只有外形的空重量共用行可以继承；它自己没有外形，解析出的重量 **不得** 再写入下一件的继承索引，避免无外形行把重量一路传下去（多继承）。
3. 仍没有 → 该序不算。

**可继承：** 与加工费共模判定同类。零件 `die_method` / `production_mode`，或本序 / 同件任一工序 `process_code` 含「合并」「双槽」「一出二」「共用」。无共模标记的空重量序不继承。上一件同序无真实长宽高则不继承（即使上一件算出了有效重量）。布点不改库：继承只发生在算费，子表快照写入 **有效重量**；`basis_text` 写明「继承 {上一件零件号} {工序} 重量」。

**该件不入库：** 没有工序、没有任何可算序、或合计 `die_fee <= 0`。不写主表，计入 `skipped_no_die_count`。

**各序**（计费用用有效重量，不按外形重算；外形核对仍只看布点本行）：

```text
line_die_fee = 有效重量 × unit_price × alloc_ratio / allocation_qty
```

`alloc_ratio` 用布点原值（共模已是 0.50，级进不再打折）。左右件各记一半：主件自有重量 × 0.50，共用件继承同一重量 × 0.50。禁止只给有重量的一侧记账。

**零件（主表是汇总）：**

```text
die_fee              = Σ 可算序 line_die_fee     # 系统模具费；必须 > 0 才落库
adjustment_amount    = 调整金额（可正可负，默认可空）
final_die_fee        = die_fee + (adjustment_amount or 0)   # 最终模具费；必须 ≥ 0
```

用户只能改 **已落库** 行上的调整金额（及备注）。`final_die_fee < 0` → PUT 400，不落库。最终可以为 0。没有系统模具费就不能改、不能手工造一行。

**入队前：** 缺年/基地/项目 → 400。该范围已有已审核 → 409。计算锁 processing → 409。

**Worker：** 无布点或无生效单价（或 `allocation_qty <= 0`）→ 任务失败，**不删旧行**。校验通过后再按下面重算。

**重算（同一年 + 基地 + 项目，可选供应商/版本）：**

- 所选身份下有已审核 → 入队前 409，不删不写。
- 所选身份全是未审核（或没有旧结果）→ **先删该身份旧结果**（未选身份则删该范围全部），再按当前布点写入匹配身份的件。调整金额、备注不保留。未选中的供应商/版本行不动。

有跳过件不算失败：整单未报错即为 `success`，跳过数只记日志。

---

## 3. 表

### 3.1 `stamping_die_fees`

唯一键：`year` + `location` + `vehicle_model` + `part_number`。

| 字段 | 说明 |
|---|---|
| 作用域 | `year`、`location`、`vehicle_model`、`part_number` |
| `source_die_part_id` | 布点主表 id，可空 |
| 快照 | `stamping_supplier`、`version`（来自布点，布点从工艺回填）、`seq_no`、`part_name`、`material`、`thickness`、`part_weight`、`die_type`、`die_method`、`production_mode`、`part_grade`、`excel_filename` |
| `price_kind` | `progressive` / `steel_plate` |
| `unit_price` | 万元/吨 |
| `allocation_qty` | 万台 |
| `die_fee` | 系统模具费（元），> 0 |
| `adjustment_amount` | 调整金额（元），可正可负，默认可空 |
| `final_die_fee` | 最终模具费（元）= 系统 + 调整，必须 ≥ 0 |
| `remark` | 调整说明 |
| 审核 | `pending` / `approved` / `rejected` + 审核 / 反审核人时点与意见 |

### 3.2 `stamping_die_fee_items`

`fee_id` 级联删除。建议唯一：`fee_id` + `process_seq`。只含 `line_die_fee > 0` 的序。

| 字段 | 说明 |
|---|---|
| `source_die_process_id` | 布点子表 id |
| `process_seq` / `process_order` / `process_code` | 工序 |
| `estimated_weight_t` / `alloc_ratio` / `die_sets` | 快照 |
| `unit_price` / `allocation_qty` / `price_kind` | 与主表同批 |
| `line_die_fee` | 本序（元），> 0 |
| `basis_text` | 计算依据 |

### 3.3 `stamping_die_fee_calc_logs`

锁：`year` + `location` + `vehicle_model`（processing 部分唯一、过期释放，对齐加工费日志）。  
快照：`stamping_supplier`、`version`（可空=该次按全部身份落库）。  
计数：`total_parts`（本次落库范围内的布点件数）、`success_count`、`skipped_no_die_count`（未入库）、`failed_count`。  
整单成功即 `success`（即使有跳过）；不要用 `partial` 表示跳过件。

---

## 4. 接口

前缀 `/api/stamping/die-fees`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/filters` | 布点级联基地/项目；年供列表下拉（可含已有结果年，计算页不依赖此项） |
| GET | `/calc/ready` | 布点零件数、可算件数（系统费将 > 0）、是否有生效单价；可带供应商/版本收窄件数 |
| POST | `/calc` | 缺参 400；已审核或锁 409；通过则 `AsyncTaskAcceptedVO`（200） |
| GET | `/calc/progress/{task_id}` | 进度 |
| GET | `/calc/logs` | 日志分页 |
| DELETE | `/calc/logs/{log_id}` | 删日志（processing 禁止） |
| GET | `/` | 必填 year + location + vehicle_model；`page`+`size`；附加筛见 §1（含供应商、版本）；排序见 §1 |
| GET | `/export` | 同列表必填范围与排序，不分页。关注点是模具费；各序另附布点外形；核对重量为 Excel 公式（长×宽×高×掏空×7.85÷10^9，四位小数），不参与计费 |
| GET | `/{id}` | 含各序 |
| PUT | `/{id}` | 仅 `adjustment_amount`、`remark`；已审核拒绝；`final_die_fee < 0` → 400 |
| DELETE | `/{id}` | 单条，仅未审核 |
| DELETE | `/scope` | 年+基地+项目，只删未审核 |
| POST | `/batch-approve` | 范围 + 意见必填 |
| POST | `/batch-reverse-audit` | 范围 + 原因必填 |

Worker 无布点/无单价 → 任务 `failed`，不是 HTTP 400。找不到记录 → 404。

任务 `result` 由切片 Service 写入辅助库 JSON；查询再做成 VO。

---

## 5. 失败与跳过

| 情况 | 行为 |
|---|---|
| 缺年 / 基地 / 项目 | 入队前 400 |
| 该范围已有已审核 | 入队前 409，不删不写 |
| 范围 processing | 409 |
| Worker 无布点 / 无生效单价或分摊万台 ≤ 0 | 任务失败，不删旧行 |
| 件无工序 / 无可算序 / 系统费 ≤ 0 | 不入库；`skipped_no_die_count`；任务仍可 `success` |
| 共用/合并行无本行重量 | 上一件同序有真实长宽高时继承有效重量再算；无外形或继承不到则该序跳过 |
| PUT 后 `final_die_fee < 0` | 400，不改库 |

---

## 6. 前端

| Hash | 标题 |
|---|---|
| `#/stamping-die-fee-calc` | 冲压模具费计算 |
| `#/stamping-die-fee` | 冲压模具费列表 |

`static/js/features/stamping/die-fee/{calc,list}/`。`pageMeta`、`app.js`、侧栏「冲压模具费」计算/列表、`?v=` 同步。

计算页：年（手填，默认当年）、基地、项目（必选），供应商、版本（附加，选项来自布点）→ 就绪（所选身份布点数 / 可算件数 / 单价）→ 计算 → 轮询；`destroy` 停轮询。历史表展示该次快照的供应商/版本；点「结果」带入列表筛。  
列表：未选齐年+基地+项目不出数。附加筛供应商、版本。列含系统模具费、调整金额、最终模具费（关键列）。单条删/改仅未审核。调整保存前校验最终 ≥ 0。操作走操作列。

---

## 7. 权限

```text
menu:stamping-die-fee-group
  menu:stamping-die-fee-calc
    op:stamping-die-fee-calc:view | run | delete
  menu:stamping-die-fee
    op:stamping-die-fee:view | update | delete | approve | reverse | export
```

---

## 8. 分层

```text
app/routers/stamping/die_fee.py
  die_fee/die_fee_service.py      列表 / 改调整金额 / 审核 / 删
  die_fee/export_service.py
  die_fee/calc/orchestrator.py    start_calc + work()
    只读布点（含工序）、模具单价
    本切片结果表 / 计算日志
```

无 Parser。`TASK_TYPE_STAMPING_DIE_FEE_CALC = "stamping_die_fee_calc"`。

---

## 9. 验收

- 未选年/基地/项目：不能算、列表/导出不请求、不能按范围删。
- 年可手填；第一次算不依赖已有结果年。
- 入队前已审核 409；Worker 无单价失败且不删旧行。
- 无已审核：先删该范围再按新布点写入（调整不保留）。
- 2 T × 5 万/吨 × 1 / 10 万台 = **1.0000 元**。系统费 ≤ 0 不入库。
- 共模：主件有长宽高且 2 T × 0.50，紧邻共用空重量件继承 2 T × 0.50，各 **0.5000 元**；共用空重量件须入库。再下一件若上一件无真实长宽高，不得再继承。
- 有跳过件时任务仍为 success。
- 调整可为负；最终 < 0 时 PUT 400。最终可以为 0。
- 未审核可单条删除。
- 列表/导出只含能算出的件，相对顺序与布点相同。
- 金额 JSON 为字符串。Model / DTO / VO / 计算 / 导出无 `float`。本期结果不进零件价、不进引擎。

---

## 10. 修订

| 日期 | 说明 |
|---|---|
| 2026-08-30 | 年度模具费：布点各序 × 模具单价；只算模具 |
| 2026-08-30 | 列表/导出：可算件保持布点相对顺序；不与 Excel 逐行一一对应 |
| 2026-08-30 | 算不出或不入库 0 费；系统 + 调整 = 最终 |
| 2026-08-30 | 重算：已审核 409；未审核先删后写 |
| 2026-08-30 | 入队前缺参 400 / 已审核与锁 409；单价与布点在 worker 失败不删旧行；年手填；列表必选范围；跳过仍 success；单条删未审核；不进零件价/引擎 |
| 2026-08-30 | 调整可负；最终模具费必须 ≥ 0，否则 PUT 400 |
| 2026-08-30 | 金额与物理量全程 `Decimal`，禁止 `float` |
| 2026-08-30 | 按设计落地：计算 / 列表 / 调整 / 审核 / 导出 |
| 2026-08-30 | 导出各序补模具编号、长宽高、掏空系数；核对重量为 Excel 公式（长×宽×高×掏空×7.85÷10^9，四位小数），仅辅助检查导入 |
| 2026-08-30 | 共模共用序无本行重量时，继承上一件同序有效重量再乘 alloc_ratio，避免共用件整件漏算 |
| 2026-08-30 | 继承上一件时该序须有真实长、宽、高；无外形行不把解析重量再传给下一件，防止多继承 |
| 2026-08-30 | 分摊万台为正整数；JSON/列表/导出写 `10`，不算四位小数 |
| 2026-08-30 | 结果快照含供应商、版本（来自布点）；列表与导出展示 |
| 2026-08-30 | 列表附加筛供应商、版本；导出可按二者收窄并写入筛选栏 |
| 2026-08-30 | 计算页附加筛供应商、版本（选项来自布点）；共模仍扫全项目，只落库/删匹配身份；日志快照身份 |
