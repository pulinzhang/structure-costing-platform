# 总成月核价（级别无关）— 详细设计

> **状态：待评审（未改业务代码）。** 本文是实施唯一口径。  
> **必须统一：** 财务成品账与采购应成本同一切片、同一公式、同一结果表；`level` 只过滤。  
> 对标：[welding-fee-design.md](../bom/welding-fee-design.md)。硬约束：[architecture.md](../architecture.md)、[orchestrator-constitution.mdc](../orchestrator-constitution.mdc)。  
> 历史（冻结、勿再分叉）：[l0-assembly-costing-design.md](l0-assembly-costing-design.md)、[l1-assembly-costing-design.md](l1-assembly-costing-design.md)。  
> 现网代码锚点：`app/services/costing/l0_assembly_cost/`（实施时整包改名）。

---

## 0. 一句话

**一次计算写出该范围全部核价卡；每张卡的根是一个 BOM 节点，公式与 `level` 无关。**  
本切片只做 **BOM walk + 间接 + 落卡**。冲压件价、焊接费一律 **抄上游已经算完并落库的行**：**零件价没算完，总成核价整趟不开始**（焊接费作业同）。单卡上某个叶子仍可能缺价，那是另一回事。年度价、包装是上传件，缺了不挡整趟。  
财务读树根卡的 `grand_total`；采购读同一批行里对象卡的 `should_cost`（=`total_amount`）。不是两套引擎。

```text
bom_welding_fees.level           = 拆解节点.level
costing_assembly_costs.level     = 核价卡根 bom_nodes.level
```

整数 0…n，不写死枚举，不建 `costing_l7_*`。

---

## 1. 评审拍板（检查用，先过这一节）

| # | 决定 | 不要做成 |
|---|------|----------|
| P1 | 一个切片 `assembly_cost`，**本切片**去尽 `l0` 前缀 | 再开 `l0`/`l1`/`outsourced` 三套表。清单 `object_kind`（`l0_degenerate` 等）是上游枚举，**照抄不改名** |
| P2 | 一行 = 一个 `source_node_id` × 年 × 月 × 范围 | 仍用零件号当唯一键 |
| P3 | 核价主体 = A∪B∪C（§4），去重按节点 | 按 level 枚举认人；再扫树发明第四套分类 |
| P4 | **永不对本卡根剪枝**；一口价只砍 **子孙** | 「根自己有年度价就不 walk」 |
| P5 | 无子件的卡根 **当叶子** 取冲压/年度价 | 继续「树根不当叶子 → 材料 0」 |
| P6 | 焊接费按 **拆解节点 `source_node_id` = 卡根** 对齐，不按 `level=0`、不按零件号字典 | `welding_by_part[part_number]` |
| P7 | 无焊接费行 → 工费 0，**不**因此 partial | 无焊就整卡失败（冲压叶子会全挂） |
| P8 | 间接 I1～I8 **每卡都算**；采购合同读 `should_cost` | `if level==0` 才算间接 |
| P9 | `should_cost` **落库且恒等于** `total_amount` | 前端自己猜用哪一列 |
| P10 | 列表默认 **财务视图 = 树根**（`parent_id IS NULL`），不是 `level=0` | 财务 = `levels=[0]`（以后更深树会错） |
| P11 | 采购视图 = join 清单 `section=object` | costing 里再实现一套 `object_kind` 分类器 |
| P12 | 计算默认 **全卡**；`levels` 可选过滤 | 引擎默认 `levels=[0]` 导致采购卡永远没有 |
| P13 | 批量审核/删除/反审 **跟当前列表筛选走**（必须带 `view`） | 财务点「全部审核」把 200+ 采购卡一起审掉 |
| P14 | 月度合册仍只出 **树根卡**（保持现网「成品账」含义） | 合册把所有 level 加总 |
| P15 | 有子件的树根 **UI 不展示** 报价对比 | 对二级开总成合同 |
| P16 | 不建 `costing_outsourced_assembly_*` | 委外第二套结果表 |
| P17 | 权限一组改名，仍两页：计算 / 一览 | 财务、采购两套菜单码 |
| P18 | BOM 重导后 `source_node_id` 可能失效 → 必须重算；迁移对不上则失败 | silently 丢历史行 |
| P19 | **冲压、焊接只读上游结果表**（见 §1.1）。缺某一叶子/节点 → 卡内 `missing` 或焊接 0，不在本切片算 `unit_cost`、不拆焊 | `prepare` 里调用零件核价 / 焊接费 Orchestrator；拆解明细 × 单价临算 |
| P20 | **计算类上游未完成 → 总成整趟不开始**（零件价、焊接费定义见 §1.2）。引擎补焊必须覆盖本趟要抄的 level，**禁止只补 `levels=[0]`** | 零件价还在 `processing` 就写卡；只补 L0 焊却按全卡抄 L1 工费 |

### 1.1 谁算、谁抄（P19）

| 金额 | 本切片 | 上游（必须先有结果行） |
|------|--------|------------------------|
| ① 冲压 | **只读** `stamping_part_costs.unit_cost`（当月、已 `success`） | 零件核价切片已按钢价/加工费/模具费算完 |
| ④⑤ 焊接 | **只读** `bom_welding_fees.final_welding_fee` / `other_fee` | 焊接费切片已按该节点拆解 × 年单价算完 |
| ②③ 年度价 / 一口价 / 报价 | **只读** `bom_annual_part_prices` | 年度价上传 |
| I1/I2 | **只读** `bom_packaging_transport_fees` | 包装运输上传 |
| I3～I6、材料加总、一口价剪枝、间接 | **本切片算** | — |

本切片的 `prepare` / `calculate` **禁止** `start_calc` 或同步调用上游 Orchestrator「补算」。

### 1.2 未完成就不下一步（P20）

总成核价是 **下游**。抄库的「计算类」上游没做完，本切片 **整趟不跑**（不是先写出一堆 `partial` 再让人猜）。

**冲压零件价（硬门，必须）：**

范围 = 总成计算的年 + 月 + 基地 + 项目。

| 视为未完成（不准进入总成核价） | 视为已完成 |
|----------------------------------|------------|
| 该项目工艺库 **一个冲压件都没有** 对应的当月 `stamping_part_costs` | 工艺库该基地+项目下、**每个冲压工厂** 的零件，当月都有结果行且 `calc_status = success` |
| 任一工厂当月仍有 `processing` 计算日志 | — |
| 任一工厂当月存在 `failed` / 无 `unit_cost` 且未补成 `success` | — |

零件核价按 **冲压工厂** 分趟算（现网日志锁 `年+月+基地+工厂`）。总成不认工厂、按零件号抄价，所以 **该项目涉及到的每一家工厂都要算完**，缺一家也不下一步。Ready / 异常文案指向零件核价页，列出未完成的工厂。

工艺库该基地+项目 **零件数为 0** → 也视为未完成（本平台总成核价不以「纯外购、无工艺」为合法空集）。

**同零件号多家工厂都有 `success`：** 抄库时若 `unit_cost` 相同，任取一条；**若不同 → 该叶子 `missing` + `match_hint=multi_supplier_unit_cost`**（不挡整趟，作业已完成，是价冲突）。禁止 `dict[part_number]` 静默后写覆盖。

硬门过了之后：某个 BOM 叶子不在工艺库（外购、标准件）→ 仍走年度价 / `missing`，那是 **单卡** 缺价，不挡整趟。不要把「作业没算完」和「这片叶子本来就不是冲压件」混成一件事。

**焊接费（同一纪律，完成定义与零件价对齐到「作业 + 覆盖」）：**

| 视为未完成 | 视为已完成 |
|------------|------------|
| 该范围仍有焊接费 `processing` 日志 | 日志非 processing / failed |
| 从未算过焊接费 | — |
| BOM 上有 `weld_info` 的节点尚未进拆解 | 有焊信的节点都有拆解行 |
| 拆解节点没有对应的 `bom_welding_fees`（按 §6 对齐当前 `source_node_id`） | **每个拆解节点一行焊接费**（允许行 `partial`，进总成后该卡 §6 partial） |
| 焊接费行的拆解/BOM 节点对不上 **当前** snapshot（重导后旧 id） | 对齐的是当前树 |

不要求「BOM 全部节点 = 焊接费行数」。无焊信 → 无拆解 → 无焊接费行，P7。

**与引擎的收口：** 现网年度补焊 `levels=[0]` **与全卡抄 L1 工费矛盾**。落地时引擎补焊改为 **不限 level**（或显式传入拆解出现过的全部 level）。只补 L0 却宣称焊接已完成 → 禁止。本切片仍不调用焊接费 `calculate`。

**上传类（年度价、包装）不是这道门：** 可以缺；卡上报价空、I1/I2=0，或叶子走年度价。不要因为没导年度价就禁止总成计算。

**引擎：** 钢价 → 零件价（各工厂）→（年度补焊若需要）→ **仅当零件价与焊接费均已完成** 才跑 assembly。零件价任一工厂失败 → 本项目 assembly **跳过**，不得抄半成品价凑总成账。本切片仍不负责去补算零件价。

---

## 2. 名词

| 对外 | 内部 | 含义 |
|------|------|------|
| 核价卡 / 本卡根 | costing root `R` | 本行对应的 BOM 节点 |
| 层级 | `level` | 抄 `bom_nodes.level` |
| 树根 | `is_tree_root` | `parent_id IS NULL` |
| 月总账 | `total_amount` | 材料 + **R 自己的** 焊接 + 焊接其它；不含间接 |
| 应成本 | `should_cost` | = `total_amount` |
| 总费用 | `grand_total` | 月总账 + 间接 |
| 一口价 | bundle | walk 中 **子孙** 有子件且命中年度价 → 剪枝 |
| 二级报价 | `vendor_quote` | R 的零件号命中年度价则该 `unit_price`（一张卡 = 一个 R 实例）；可空 |
| 价差 | `gap_amount` | 有报价：`vendor_quote - should_cost`；无报价：NULL |
| 所属供货件 | `root_part_number` | 从 R 上溯到树根的零件号（退化件 = 自己） |

**禁止**把不同卡、不同 `level` 的金额加总当应付。父卡材料已含（或一口价替代）子树；子卡是另一读者的工费卡。

---

## 3. 共用公式（与 level 无关）

对每个核价主体 `R`：

```text
材料 walk（§5）
  ① stamping_amount  ② purchased_amount  ③ bundle_amount
  material_amount = ①+②+③

工艺（**抄** R 自己已落库的焊接费行，§6；不重算）
  welding_amount    = final_welding_fee   // 无行 = 0
  welding_other_fee = other_fee           // 无行 = 0

月总账
  total_amount = material + welding + welding_other
  should_cost  = total_amount

间接 I1～I8（§7）每卡都写
  grand_total = total_amount + indirect_amount

报价（可空）
  年度价命中 R.part_number → vendor_quote = unit_price，vendor_name = supplier_name
  否则 vendor_quote / gap_amount / vendor_name 全空（不 failed）
  有报价 → gap_amount = vendor_quote - should_cost
```

金额恒等式（写死，persist 前校验，对不上则该卡 `failed`）：

```text
material_amount      = stamping + purchased + bundle
total_amount         = material + welding + welding_other
should_cost          = total_amount
allocation_fee_total = gauge_alloc_fee + fixture_alloc_fee
indirect_amount      = I1+I2+I3+I4+I5+I6 + allocation
grand_total          = total_amount + indirect_amount
```

`formula_version` = `assembly-v1`（替换 `l0-assembly-v1`）。

**抄库键（只 SELECT，不写上游表）：**

| 价 | 匹配 | 禁止 |
|----|------|------|
| 冲压 `unit_cost` | 年 + 月 + 基地 + 项目 + 零件号；须 `calc_status=success`；**不认**冲压工厂；不跨基地。多工厂冲突见 §1.2 | 从钢价、加工费再推 `unit_cost`；静默覆盖不同工厂的不同单价 |
| 焊接 | 年 + 基地 + 项目 + BOM 版本 + 拆解行的 `source_node_id = R.id` | 读拆解明细 × `bom_welding_unit_price`；调焊接费 `calculate` |
| 年度价 / 一口价 / 报价 | 基地 + 年 + 零件号 | 本切片维护价表 |
| 包装 I1/I2 | 基地 + 年 + **本卡**零件号（不加车型） | 本切片上传包装 |
| 费率 I3～I6 | `system_configs` 单例 × 本卡 `total_amount` | — |

---

## 4. 计谁

### 4.1 并集（一次 `prepare` 算完）

```text
nodes = 该 snapshot 全部 bom_nodes
parent_ids = { n.parent_id | n.parent_id 非空 }

A = { n | n.id ∈ parent_ids }              // 有子件
B = { n | n.parent_id is NULL }            // 树根（含退化）
C = ∅
若存在该范围采购对象清单：
  C = { bom_nodes 中 id = object.source_node_id
        | section = object }

subjects = A ∪ B ∪ C                       // 按 id 去重
若 dto.levels 非空：
  subjects = { n ∈ subjects | n.level ∈ levels }
```

| 典型成员 | 来源 |
|----------|------|
| 有子件的供货总成 | A∩B |
| 退化供货件 | B，且常在 C（`l0_degenerate`） |
| 分总成 | A，且常在 C（`l1_subassembly`） |
| L1 冲压件 | 几乎只在 C（`l1_stamping`） |

**不出卡：** 分总成下的 L2、核对区 `other_leaf` / `anomaly`。它们只出现在某张卡的 `items`。

清单未生成：仍算 A∪B（财务不堵）；C 类冲压叶子要等清单。  
`confirm_status` **不算不算卡**；只影响采购视图筛选与合同列展示。未确认也出候选应成本。

有子件的树根永不在 C（清单已保证）。仍出财务卡；UI 隐藏报价对比（P15）。

### 4.2 芜湖 T13J / `D/09` 期望卡数（主库盘点，作结构验收）

| 集合 | 约数 |
|------|------|
| 节点 | 357（L0 44 / L1 205 / L2 108） |
| A 有子件 | 83 |
| B 树根 | 44（其中无子件 14） |
| C 采购对象 | 14 + 53 + 132 |
| 全卡 A∪B∪C | **229** |
| 现网成品账行 | 44（仅树根） |
| 焊接费 2026 | L0=36，L1=53（与分总成 53 对齐） |

深度：`l2plus_with_children = 0`。T13J **测不出** 4 层递归，4 层必须用单元夹具。T13J 2026 **无年度价、无包装** → 测不出一口价/`vendor_quote`/I1I2；金标仍用青岛 T28 2025-01 + 人工带价夹具。

---

## 5. 材料 walk

### 5.1 用量

- 卡头 `supply_qty` = `R.qty`（相对父；树根常见 1）。
- 明细 `effective_qty` = 从 **R 的直接子节点** 走到该节点的 `qty` 连乘（**不含** `R.qty`）。
- 现网 L0→L1→L2：叶子 = `L1.qty × L2.qty`（与 `l0_assembly_sim` 一致）。
- `R` 无子件：一行叶子，`effective_qty = 1`。库内金额 = **一个 R 实例**。单车展示 = 金额 × `supply_qty`（列表可选列，默认财务树根 `supply_qty` 多为 1，不必强调）。

### 5.2 递归（替换 `rollup_l0` 两层 for）

**P4：不对 R 自己做一口价判断。** 即使 R 有年度价，仍 walk 子件（采购应成本）；R 的年度价只进 `vendor_quote`。

```text
function walk(node, path_qty):
  kids = children[node.id] 按 sort_no, id
  if kids 为空:
      emit 叶子取价(node, path_qty)          // §5.3
      return
  for D in kids:
      q = path_qty * D.qty
      if D 有子件 and D.part_number in annual_prices:
          emit bundle(D, q)
          for 每个 D 的后代 G:
              emit skipped_by_bundle(G, path_qty_from_R_to_G, hint=D.part_number)
              // path_qty_from_R_to_G = 从 R 的直接子走到 G 的 qty 连乘（规则同 §5.1）
      elif D 有子件:
          walk(D, q)
      else:
          emit 叶子取价(D, q)

入口:
  if R 无子件: walk 等价于 叶子取价(R, 1)
  else:        对每个直接子 D: 按上式（path_qty 从 1 起，第一层乘 D.qty）
```

`skipped_by_bundle`：单价/金额 0，保留 `effective_qty`；不进 ①②。

同零件号多分支：分别计价后 **相加**（现网规则）。

### 5.3 叶子取价（写死）

1. 完整零件号 → **已落库**的当月冲压 `unit_cost`（只读，不重算零件核价）  
2. 否则完整零件号 → **已落库**年度价（`0` = 金额 0，**不是**缺价）  
3. 否则零件号含 `-` → 第一个 `-` 之前 **只回退已落库冲压价**

都没有 → `cost_source=missing`，`missing_leaf_count += 1`。

`cost_source`：`stamping` / `annual` / `bundle` / `skipped_by_bundle` / `missing`。

明细不再写 `L1-leaf` / `L2`。改存 `node_level`（该明细节点的 `bom_nodes.level`）。卡根本身当叶子时 `node_level = R.level`。

---

## 6. 焊接费对齐（现网最大坑）

本卡 ④⑤ **只抄** `bom_welding_fees` 已有行（P19）。没有行就 0，**不要**在总成核价里用拆解明细临算工费。

现网 prep：`list_by_calc_scope(..., level=0)` 再 `welding_by_part[part_number]`。同号两支会撞；L1 工费进不来。对齐方式要改，仍是 **读表**，不是改去算焊。

**正确对齐：**

```text
breakdown_by_bom_node = { bn.source_node_id: bn.id | 该范围拆解主表 }
welding_by_bom_node   = { bd.source_node_id: fee
                          | fee.source_breakdown_node_id = bd.id
                          | 该范围年+基地+车型+BOM版本 }
本卡 welding = welding_by_bom_node.get(R.id)
```

不要用 `fee.level` 分支。`fee.level` 应等于 `R.level`，不等则记 `calc_message` 警告，仍用该行金额（拆解抄层，以拆解为准）。

| 有无行 | 金额 | partial |
|--------|------|---------|
| 有，且该行 `calc_status` 为 ok | 抄 `final_welding_fee`（空则 `total_welding_fee`）和 `other_fee` | 否 |
| 有，且缺单价 / partial / failed | 仍抄能抄的金额 | **是** |
| 无行 | 0 | **否**（P7） |

父卡不累加子卡焊接。`rolled_in_parent` 已含在父节点自己的年结果里；子卡读子节点自己那一行。

---

## 7. 间接、报价、状态

### 7.1 间接（与现网 I1～I8 同码）

每卡 8 行，金额 0 也落 `costing_assembly_cost_indirects`。主表宽列同步。

| sort | code | 来源 |
|------|------|------|
| 1 | `unit_transport_fee` | 包装 `unit_transport_fee`；无行 0 |
| 2 | `warehouse_bundling_fee` | 包装 `other_fee`；**勿用** `packaging_transport_total` |
| 3–6 | 财务/管理/报废/税前利润 | 本卡 `total_amount ×` 系统费率 |
| 7–8 | `gauge_alloc_fee` / `fixture_alloc_fee` | 上游未建 = 0，仍进 `grand_total` |

无包装 **不** partial。  
采购列表默认不展示间接列，读 `should_cost`。  
非树根卡 I1/I2 常为 0（包装挂在供货号上）——数据，不是公式分支。

### 7.2 报价

- 否决「没年度价就不算卡」。
- `vendor_name` 只来自年度价 `supplier_name`。禁止 `material_mill`。
- 树根有子件：仍可写入 `vendor_quote`（若命中），**列表财务/采购对总成行都不展示价差**（P15）。采购视图根本没有这类行（不在 C）。

叶子卡：应成本走 §5.3（可能是冲压），`vendor_quote` 仍是年度价 → `gap` 有业务意义。

### 7.3 `calc_status`

| 条件 | 状态 |
|------|------|
| 无 missing 叶子，焊接行完整或无焊接行 | `ok` |
| missing 叶子 > 0，或焊接行不完整 | `partial` |
| 恒等式失败、未捕获异常（单卡 SAVEPOINT） | `failed`（该卡）；任务仍继续其它卡 |

无报价、无包装、无 `vendor_name` → 不影响状态。

---

## 8. 表结构

一次迁移、不双写。SQLite 现网表改名（与焊接费迁表同一策略）。

```text
costing_assembly_costs
 ├── costing_assembly_cost_items
 └── costing_assembly_cost_indirects
costing_assembly_cost_calc_logs
```

### 8.1 主表 `costing_assembly_costs`

**唯一约束：** `(year, month, location, vehicle_model, bom_version, source_node_id)`  
建议索引：范围+`level`；范围+`is_tree_root`；`part_number`；`calc_status`；`audit_status`；`calc_batch_id`。

| 分组 | 字段 | 说明 |
|------|------|------|
| Scope | `year`,`month`,`location`,`vehicle_model`,`bom_version` | |
| 根 | `source_node_id` | `bom_nodes.id`，必填 |
| | `level` | 抄节点 |
| | `is_tree_root` | `parent_id IS NULL`，必填布尔（SQLite Integer 0/1） |
| | `parent_node_id` | 可空 |
| | `root_part_number`,`root_part_name` | 所属供货件快照 |
| | `part_number`,`part_name`,`supply_qty`,`sketch_url` | 本卡根 |
| | `bom_snapshot_id` | 可空 |
| | `procurement_object_id` | 可空，命中 C |
| | `object_kind` | 可空快照：`l0_degenerate` / `l1_subassembly` / `l1_stamping` |
| 月总账 | 现网 ①②③ 材料/焊/其它/`total_amount` | 保留 |
| | `should_cost` | = `total_amount` |
| 间接宽列 | 现网 I1～I8 / `indirect_amount` / `grand_total` | 保留 |
| 报价 | `vendor_quote`,`gap_amount` | Numeric 可空 |
| | `vendor_name` | 可空 |
| 费率快照 | 四个 rate | 保留 |
| 焊接 | `welding_fee_id`,`welding_summary` | 任意 level |
| 状态 | `calc_status`,`missing_leaf_count`,`calc_message`,`formula_version`,`calculated_at`,`calc_batch_id` | |
| 审核 / 审计 | 与现网同构 | 已审禁止覆盖 |

### 8.2 明细 `costing_assembly_cost_items`

FK `assembly_cost_id` 级联删。废止 `level_label`。

| 字段 | 说明 |
|------|------|
| `node_level` | int，明细节点层级 |
| `bom_node_id` | 可空 |
| `part_number`,`part_name`,`node_role`,`supply_type` | |
| `cost_source` | 见 §5.3 |
| `match_hint` | 如 `dash_fallback:` / `bundle_parent:` |
| `unit_price`,`effective_qty`,`line_amount`,`sort_no` | |

行唯一：`(assembly_cost_id, sort_no)` 即可（现网还拼了 part+source，同号两支靠 sort_no 区分）。实施时改为 `(assembly_cost_id, sort_no)` 唯一。

### 8.3 间接子表

与现网相同：`(assembly_cost_id, code)` 唯一。`code` 表见 §7.1。

### 8.4 计算日志

锁仍按 **年+月+基地+车型+BOM 版本**（一次任务写全部卡，不含 `source_node_id`）。字段去 `l0` 前缀。processing 部分唯一索引规则与现网一致。

### 8.5 迁移算法

1. 改名四张表（主/明细/间接/日志）。  
2. 主表加新列；旧唯一键 `(…, part_number)` 改为 `(…, source_node_id)`。  
3. 已有行：用当时 `bom_snapshot_id`（空则按范围找 snapshot）+ `part_number` + **`level=0` 且 `parent_id IS NULL`** 匹配树根。  
   - 匹配 1 个节点 → 回填。  
   - 0 或多个 → **整批迁移失败**，列出冲突，禁止丢行。  
4. 明细：`level_label` → `node_level`（`L2`→2，`L1-leaf`/`L1-bundle`→1；未知则失败）。  
5. `should_cost = total_amount`；报价列空；`is_tree_root=1`。  
6. 不自动生成历史非树根卡；缺的卡靠重算。

---

## 9. 计算编排

指挥家：`prepare → BatchEngine.run → persist`。`calculate` 禁 for。BatchEngine 按 `subjects` 循环 + SAVEPOINT（现网已有）。

```text
prep（全部 SELECT 已落库数据，禁止调用上游 calculate）:
  载入 snapshot 节点、children 字典
  算 subjects（§4.1）
  冲压价 dict[part_number]          ← stamping_part_costs
  年度价 dict[part_number] + supplier_name
  焊接 map[bom_node_id]（§6）       ← bom_welding_fees
  包装 dict[part_number]
  费率
  清单 C 的 source_node_id → object_id / object_kind

engine:
  已审跳过（按新业务键）
  rollup_assembly(R, …)
  upsert 主表 + 替换明细

persist:
  提交、写日志终态、释放锁
```

**Ready（计算页，P20）：**

| 条件 | ready |
|------|--------|
| 无 snapshot | 否 |
| A∪B 为空 | 否 |
| 冲压零件价未完成（§1.2） | **否**（文案列未完成工厂，跳转零件核价） |
| 焊接费计算未完成（§1.2） | **否**（跳转焊接费计算） |
| 其余 | 是 |

`calculate` 与 Ready 同一套门：未完成直接 `BusinessException`，不写总成卡、不入队装成「先算着」。

Ready VO 增加：`subject_count`、`tree_root_count`、`procurement_object_count`、`welding_fee_count`（全 level）、`welding_fee_level_counts`、`stamping_complete`、`stamping_incomplete_suppliers`、`welding_calc_complete`。保留 `l0_count` 一期别名 = `tree_root_count`（避免旧前端崩），随后删除。

缺清单：警告「采购对象未生成，本趟只出装配∪树根」（不挡计算）。年度价/包装为 0：黄灯，不挡。

---

## 10. API / 权限 / 页面

### 10.1 路径

| 现网 | 目标 |
|------|------|
| `/api/costing/l0-assembly-costs` | `/api/costing/assembly-costs` |
| `#/l0-assembly-cost-calc` `#/l0-assembly-cost` | `#/assembly-cost-calc` `#/assembly-cost` |
| 侧栏「成品核价」 | 「总成核价」（计算 / 一览） |

旧 API 一期 **307** 到新路径（方法+body 保留）。旧 hash 在 `app.js` 重定向。禁止长期双写两套 Router 逻辑。

任务类型：`assembly_cost_calc`。引擎阶段 id：`assembly`（替换 `l0`）。

### 10.2 JSON 接口（仍 `ApiResponse[T]`）

现网计算/列表/详情/批量审删/导出/筛选年 **能力保留**，前缀更换。

计算 DTO 增加可选 `levels: list[int] | None = None`。

列表 Query 增加：

| 参数 | 说明 |
|------|------|
| `view` | `finance`（默认）= `is_tree_root`；`procurement` = `procurement_object_id IS NOT NULL`；`all` = 不限 |
| `level` | 可选 int |
| `object_kind` | 可选 |
| `confirm_status` | 仅采购视图：live join 清单，不写进结果表 |

批量 DTO **必须带 `view`**（与列表默认相同 `finance`）。禁止无 view 的「范围全表审核」。

详情 VO 带 `items` + `indirects`；列表主表即可。

金额 JSON：VO `@field_serializer` 字符串，现网约定不变。

### 10.3 权限（一次性改名 + 库内码替换）

| 现网 | 目标 |
|------|------|
| `menu:l0-assembly-cost-group` | `menu:assembly-cost-group` |
| `menu:l0-assembly-cost-calc` + `op:l0-assembly-cost-calc:*` | `menu:assembly-cost-calc` / `op:assembly-cost-calc:view\|run\|delete` |
| `menu:l0-assembly-cost` + `op:l0-assembly-cost:*` | `menu:assembly-cost` / `op:assembly-cost:view\|delete\|approve\|reverse\|export` |

`docs/permission-design.md` 与 `Perm.*`、角色种子、前端 `can()` **同步改**。一期可在 `canAccessPage` 把旧 pageName 映射到新码，避免未迁角色的账号空白。不新增第二组「应成本」菜单。

### 10.4 前端

目录：`static/js/features/costing/assembly-cost/{calc,list}/`。`?v=` 递增。`index.html` 侧栏 `data-page`。`pageMeta` 标题「总成核价计算 / 总成核价一览」。

一览：

- 默认 `view=finance`，表头仍偏总费用 / 间接（现网 HUD）。  
- 切换采购：列改为应成本、工艺费（`welding_amount`）、报价、价差、`object_kind`、确认状态（join）；不展示 I3～I8。  
- 操作仍只在操作列。  
- 有子件树根不出现在采购视图。

计算页：就绪展示树根数 / 主体数 / 清单对象数 / 各层焊接行数。开始计算 = 全卡（不在页面默认勾 `levels=[0]`）。

导出（一览）：跟当前 `view` 筛。合册（引擎月报）只树根（P14）。

---

## 11. 现网横切改造清单（实施时按此搜）

| 区域 | 现网符号 |
|------|----------|
| 包 | `app/services/costing/l0_assembly_cost/**`、`app/routers/costing/l0_assembly_cost/**`、`app/repositories/costing/l0_assembly_cost/**` |
| 模型 / schema | `L0AssemblyCost*`、`l0_assembly_cost_{dto,vo}` |
| 引擎 | 零件价完成且 **焊接费覆盖全部要抄的 level** 才跑 assembly（P20）。补焊 **禁止** 只传 `levels=[0]`。阶段 id `l0` → `assembly`。`annual_l0_welding_fee` 阶段可改名为 `annual_welding_fee`（实施时与引擎文档一起改）。本切片不得内部触发上游 |
| 合册 | `monthly_bundle_export_service` → 树根过滤 |
| LLM | `menu_catalog`、`field_labels`、`cost_analysis_repository` |
| 权限 / 种子 | `codes.py`、`permission-design.md` |
| 前端 | `index.html`、`app.js`、`features/index.js`、`l0-assembly-cost/` |
| 测试 | `tests/costing/l0_assembly_sim.py` 改为 `assembly_sim.py`；青岛金标加「仅树根 + 有子件」过滤；退化根单独用例 |
| 任务常量 | `TASK_TYPE_L0_ASSEMBLY_COST_CALC` |

焊接费切片、采购对象清单切片 **不改公式**。costing 只读它们。

---

## 12. 验收

| 项 | 口径 |
|----|------|
| 青岛 T28 2025-01 有子件树根 | 与现网 `l0_assembly_sim` 分项金额一致 |
| 青岛退化树根 | **允许与旧模拟不同**（现网材料 0 → 现当叶子）；单独列 diff |
| 4 层夹具 | 递归、中间层一口价剪枝、子卡打开子树 |
| 同号两支 | 两张卡或两行明细，金额相加；焊接按节点不撞号 |
| T13J 芜湖 2026-01 `D/09` | 卡数 229；采购 53 张分总成卡 `welding` 能对上 53 行 L1 焊接费；14 张退化卡材料非 0（有冲压则 ok）；无年度价故无 bundle/quote，大量 `partial` 可接受 |
| 恒等式 | persist 前每卡检查 |
| 合册 | 行数 = 树根数，不是 229 |

---

## 13. 落地顺序

```text
D0  本文评审通过（§1 现为 P1～P20）
D1  纯函数 rollup_assembly + 青岛/夹具/T13J 结构测试（先测后迁表）
D2  表改名 + 迁移；切片/API/权限/前端去 l0
D3  列表双视图；批量带 view；引擎阶段 assembly 默认全卡
D4  合册只树根；LLM 目录；旧 URL 重定向
D5  退化树根财务专项签字
```

未评审通过前 **不改业务代码**。

---

## 14. 做 / 不做

| 做 | 不做 |
|----|------|
| 统一切片与公式 | 第二套应成本表 / 第二套 rollup 开关 |
| 换根打开子树 | 有子件树根对二级总成合同 |
| 树根当叶子（无子件时） | 财务材料长期为 0 |
| 间接每卡都算、读者选列 | `if level` |
| 批量跟视图 | 无 view 的全表审核 |
| 抄已算完的冲压零件价、焊接费；未完成则整趟不开始 | 零件价还在算/失败就写总成卡；替上游算零件核价或焊接费 |

---

## 15. 相关文档

| 文档 | 角色 |
|------|------|
| [l0-assembly-costing-design.md](l0-assembly-costing-design.md) | 现网五块积木、I1～I8、青岛样例 |
| [l1-assembly-costing-design.md](l1-assembly-costing-design.md) | 应成本口径；§7 委外表 **作废** |
| [welding-fee-design.md](../bom/welding-fee-design.md) | 按节点工费 |
| [bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md) | 集合 C |
| [costing-engine-design.md](costing-engine-design.md) | 阶段改为全卡 |
| [permission-design.md](../permission-design.md) | 改名 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-01 | 初稿：合并两本账、级别无关。 |
| 2026-09-01 | 详细设计：十八条拍板；卡根不剪枝；焊接按拆解 `source_node_id`；财务=树根而非 level=0；批量必须带 view；全表字段/API/权限/迁移/T13J 卡数。 |
| 2026-09-01 | **P19：** 冲压、焊接（及年度价/包装）只抄上游已落库结果；本切片不替上游计算。引擎可先跑上游阶段，`prepare` 不得调用上游 Orchestrator。 |
| 2026-09-01 | **P20：** 冲压零件价（及焊接费作业）未完成则总成核价整趟不开始；与单卡叶子缺价区分。 |
| 2026-09-01 | 落地检查收口：P1 不改清单 `object_kind`；多工厂同号单价冲突；焊接完成=当前树每个拆解节点有费行；引擎补焊不得只 `levels=[0]`；工艺库 0 件视为未完成。 |
