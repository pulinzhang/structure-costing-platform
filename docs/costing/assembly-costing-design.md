# 总成月核价（级别无关）— 详细设计

> **状态：已落地。** 本文是实施唯一口径。  
> **必须统一：** 财务成品账与采购应成本同一切片、同一公式、同一结果表；`level` 只过滤。  
> 对标：[welding-fee-design.md](../bom/welding-fee-design.md)。硬约束：[architecture.md](../architecture.md)、[orchestrator-constitution.mdc](../orchestrator-constitution.mdc)。  
> 历史（冻结、勿再分叉）：[l0-assembly-costing-design.md](l0-assembly-costing-design.md)、[l1-assembly-costing-design.md](l1-assembly-costing-design.md)。  
> 现网代码锚点：`app/services/costing/assembly_cost/`。

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
| P4 | 卡根**有子件且命中年度价** → 本卡按外购件落账（年度价已含工费），子孙 `skipped_by_bundle`，**不报缺价、不抄本卡焊接**；一口价同样砍 walk 中的子孙。判定函数 `codes.is_purchased_assembly_root`；对外说明句 `codes.PURCHASED_ASSEMBLY_NOTE`（核算报告 / 计算过程共用） | 外购件总成仍拆子件 / 再加焊，把已含件报缺价；文案各写各的 |
| P5 | 无子件的卡根 **当叶子** 取冲压/年度价 | 继续「树根不当叶子 → 材料 0」 |
| P6 | 焊接费按 **拆解节点 `source_node_id` = 卡根** 对齐，不按 `level=0`、不按零件号字典 | `welding_by_part[part_number]` |
| P7 | 无焊接费行 → 工费 0，**不**因此 partial | 无焊就整卡失败（冲压叶子会全挂） |
| P8 | 间接 I1～I8 **每卡都算**；采购合同读 `should_cost` | `if level==0` 才算间接 |
| P9 | `should_cost` **落库且恒等于** `total_amount` | 前端自己猜用哪一列 |
| P10 | 列表默认 **财务视图 = 树根**（`parent_id IS NULL`），不是 `level=0` | 财务 = `levels=[0]`（以后更深树会错） |
| P11 | 采购视图 = join 清单 `section=object` | costing 里再实现一套 `object_kind` 分类器 |
| P12 | 计算默认 **全卡**；`levels` 可选过滤 | 引擎默认 `levels=[0]` 导致采购卡永远没有 |
| P13 | 批量审核/删除/反审 **跟当前列表筛选走**（必须带 `view`） | 财务点「全部审核」把 200+ 采购卡一起审掉 |
| P14 | 月度合册仍只出 **树根卡**（保持现网「成品账」含义）；合册 API **无** `view` | 合册把所有 level 加总；合册跟采购视图 |
| P15 | 有子件的树根 **UI 不展示** 报价对比 | 对二级开总成合同 |
| P16 | 不建 `costing_outsourced_assembly_*` | 委外第二套结果表 |
| P17 | 权限一组改名，仍两页：计算 / 一览 | 财务、采购两套菜单码 |
| P18 | BOM 重导后 `source_node_id` 可能失效 → 必须重算；迁移对不上则失败 | silently 丢历史行 |
| P19 | **冲压、焊接只读上游结果表**（见 §1.1）。缺某一叶子/节点 → 卡内 `missing` 或焊接 0，不在本切片算 `unit_cost`、不拆焊 | `prepare` 里调用零件核价 / 焊接费 Orchestrator；拆解明细 × 单价临算 |
| P20 | **计算类上游未完成 → 总成整趟不开始**（零件价、焊接费定义见 §1.2）。引擎补焊必须覆盖本趟要抄的 level，**禁止只补 `levels=[0]`** | 零件价还在 `processing` 就写卡；只补 L0 焊却按全卡抄 L1 工费 |
| P21 | **树根卡 ④⑤ 与现网成品账相同：只抄该树根自己的焊接费行，禁止把下级焊接费加进树根。** 手工表焊信写在供货总成上，已是整台总成（含总成自己焊、也含填表时从各处汇总进来的量），下级行不能拿来旁证或加总 | `welding_amount(树根) = Σ 子孙焊接费`；用 L1 工费去「修正」L0 |
| P22 | **导出按角色分册。** 财务：成品核价册 + 核对合册（只树根）。采购：应成本册（对象卡 + 该卡材料/焊费，**无** I3～I8 Sheet、**无** 合册价表）。同一结果表，两套 Excel | 采购点合册；合册带 `view=procurement`；采购册带间接列 |

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
| 该项目工艺库 **有冲压件** 但当月 `stamping_part_costs` 未齐 | 无冲压工艺（零件数为 0）→ **跳过**零件价完成检查，不挡总成；有工艺则每个冲压工厂当月都有结果行且 `calc_status = success` |
| 任一工厂当月仍有整车 `processing` / `failed` 计算日志（锁 `全部工厂`） | — |

零件核价按 **基地 + 项目** 一趟算（现网日志锁 **年 + 月 + 基地 + 项目**，`stamping_supplier` = `全部工厂`）。总成不认工厂、按零件号抄价，所以 **该项目工艺库涉及到的每一家冲压工厂都要算完**，缺一家也不下一步。Ready / 异常文案指向零件核价页，列出未完成的工厂。**不过**供应商主数据 `require_enabled`（见 [supplier-design.md](../masterdata/supplier-design.md) S14）。

工艺库该基地+项目 **零件数为 0**（无冲压工艺）→ **不判**零件价是否完成，总成仍可开始（与核价引擎一致：无工艺不去判冲压加工费/零件价）。有工艺才要求各厂零件价算完。

**同零件号多家工厂都有 `success`：** 抄库时若 `unit_cost` 相同，任取一条；**若不同 → 该叶子 `missing` + `match_hint=multi_supplier_unit_cost`**（不挡整趟，作业已完成，是价冲突）。禁止 `dict[part_number]` 静默后写覆盖。

硬门过了之后：某个 BOM 叶子不在工艺库（外购、标准件）→ 仍走年度价 / `missing`，那是 **单卡** 缺价，不挡整趟。不要把「作业没算完」和「这片叶子本来就不是冲压件」混成一件事。

**焊接费（同一纪律，完成定义与零件价对齐到「作业 + 覆盖」）：** 无含 L0 的 BOM 则总成不开始、也不判焊接费。有 BOM 时：

| 视为未完成 | 视为已完成 |
|------------|------------|
| 该范围最新焊接费日志为 `processing` / `failed`（历史 `partial` 不算） | 最新日志为 `success` 或 `partial`，且当前费行覆盖见下行 |
| 从未算过焊接费 | — |
| BOM 上有 `weld_info` 的节点尚未进拆解 | 有焊信的节点都有拆解行 |
| 拆解节点没有对应的 `bom_welding_fees`（按 §6 对齐当前 `source_node_id`） | **每个拆解节点一行焊接费**（允许行 `partial`，进总成后该卡 §6 partial） |
| 焊接费行的拆解/BOM 节点对不上 **当前** snapshot（重导后旧 id） | 对齐的是当前树 |

不要求「BOM 全部节点 = 焊接费行数」。无焊信 → 无拆解 → 无焊接费行，P7。

**与引擎的收口：** 现网年度补焊 `levels=[0]` **与全卡抄 L1 工费矛盾**。落地时引擎补焊改为 **不限 level**（或显式传入拆解出现过的全部 level）。只补 L0 却宣称焊接已完成 → 禁止。本切片仍不调用焊接费 `calculate`。

**上传类（年度价、包装）不是这道门：** 可以缺；卡上报价空、I1/I2=0，或叶子走年度价。不要因为没导年度价就禁止总成计算。

**引擎：** 钢价 → 有工艺才跑零件价 →（有 BOM 才年度补焊）→ 有 BOM 才跑 assembly。无工艺不因零件价未做而跳过总成；有工艺且零件价失败 → 本项目 assembly **跳过**。无 BOM 不判焊接、不跑总成。本切片仍不负责去补算零件价。

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
| 一口价 | bundle | **本卡根**或 walk 中 **子孙** 有子件且命中年度价 → 剪枝 |
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

工艺（**抄** R 自己已落库的焊接费行，§6；不重算、**不把子孙焊接费加进来**）
  welding_amount    = final_welding_fee   // 无行 = 0
  welding_other_fee = other_fee           // 无行 = 0

月总账
  total_amount = material + welding + welding_other
  should_cost  = total_amount

间接 I1～I8（§7）每卡都写
  grand_total = total_amount + indirect_amount

报价（可空）
  年度价命中 R.part_number → vendor_quote = unit_price，vendor_name = supplier_name（价表档案原文；不过供应商 `require_enabled`）
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

### 4.2 芜湖 T13J / `D/09` 实盘（对照硬门）

**2026-09-01 再盘（用户已手工整理上游后，snapshot `id=1`）：**

| 项 | 实数 | 对落地 |
|----|------|--------|
| BOM | 357 节点（L0 44 / L1 205 / L2 108）；树根 44（无子件 14）；有子件 83；`weld_info` 89 | 结构未变 |
| 冲压工艺 | 4 厂共 **89** 件 | |
| 零件价 2026-01 | 89/89 `success`；无跨厂同号；无单价冲突 | **P20 冲压硬门通过** |
| 拆解 / 焊接费 2026 | 各 89 行（L0=36、L1=53），费行全 `ok`，`source_node_id` 对应当前树，无 stale | **P20 焊接覆盖通过**（最新计算日志 `success`；更早 8 条 `partial` 是历史，**不挡**） |
| 年度价 芜湖 2026 | **7** 条，全是叶子紧固件号，**无一有子件** | 仍测不出一口价剪枝；可测叶子年度价 / `vendor_quote`（若该件出卡） |
| 包装 | **0** | I1/I2 全 0，不挡 |
| 采购对象清单 | **0**（表空） | C=0；本趟只能出 **A∪B=97** 张卡，不是 229。要测 132 张 L1 冲压卡须 **重新生成清单** |
| 现网成品账 | 44 行，`bom_snapshot_id=2` | 当前树已是 snapshot **1**（同版本 D/09 重导）。迁移不得死盯旧 id=2，须按范围+树根零件号回填（P18） |

深度仍无 L2 再带子件。一口价 / 打开子树金标仍用青岛或人工夹具。

**P20 以当前库：零件价+焊接费已齐，独立计算页可以开总成核价（97 张卡）。** 采购视图会空，直到清单再生成。

---

## 5. 材料 walk

### 5.1 用量

- 卡头 `supply_qty` = `R.qty`（相对父；树根常见 1）。
- 明细 `effective_qty` = 从 **R 的直接子节点** 走到该节点的 `qty` 连乘（**不含** `R.qty`）。
- 现网 L0→L1→L2：叶子 = `L1.qty × L2.qty`（与 `l0_assembly_sim` 一致）。
- `R` 无子件：一行叶子，`effective_qty = 1`。库内金额 = **一个 R 实例**。单车展示 = 金额 × `supply_qty`（列表可选列，默认财务树根 `supply_qty` 多为 1，不必强调）。

### 5.2 递归（替换两层 for）

**P4：卡根自己有子件且命中年度价，按外购件/一口价落账。** 子孙已含在该年度价里，写 `skipped_by_bundle`，不走叶子取价、不计入 `missing_leaf_count`。年度价已是结算价，**本卡 ④⑤ 记 0、不挂焊接费行、不因上游焊费 partial**。`vendor_quote` 仍是该年度价（与一口价相同，价差 0）。无子件的卡根仍按 P5 当叶子，焊接仍按 P6 抄。

```text
function walk(node, path_qty):
  kids = children[node.id] 按 sort_no, id
  if kids 为空:
      emit 叶子取价(node, path_qty)          // §5.3
      return
  if node.part_number in annual_prices:      // 含本卡根：外购件总成
      emit bundle(node, path_qty)
      for 每个 node 的后代 G:
          emit skipped_by_bundle(G, path_qty_from_R_to_G, hint=node.part_number)
      return
  for D in kids:
      walk(D, path_qty * D.qty)

入口: walk(R, 1)
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

## 6. 焊接费：只抄本卡根，树根口径与现网 L0 相同（P21）

### 6.1 为什么树根不能加下级焊费

材料清单上 **供货总成（树根）的焊信是整台总成的工费原文**：总成自己也可能焊，填手工表时各层焊点也往往 **汇总写在这一格**。上游焊接费按该格拆解 × 单价，已经是财务认的那一笔。

下级（分总成）即使另有焊信、另有焊接费行，那是给采购应成本用的 **另一张工费卡**，不能拿来旁证树根、更不能加进树根 `welding_amount`。加总会和手工表双计。

因此：**统一切片、多卡并行，不改变现网树根卡的焊接口径。** 变的是多写出子卡；不是改树根公式去吃下级焊费。

材料侧故意变更（P5 无子件树根当叶子）与本条无关。④⑤ 保持现网。

### 6.2 每卡仍只抄自己那一行

本卡 ④⑤ **只抄** `bom_welding_fees` 里 **R 自己** 的已落库行（P19）。没有行就 0，**不要**用拆解明细临算，**不要** `Σ children.welding_amount`。**例外（P4）：** 卡根有子件且命中年度价 → 外购件一口价已含工费，④⑤ = 0，不挂 `welding_fee_id`。

现网 prep：`list_by_calc_scope(..., level=0)` 再 `welding_by_part[part_number]`。同号两支会撞。对齐方式要改成按节点，树根仍只取 **该树根节点** 那一行（通常就是现网的 L0 行）。

```text
breakdown_by_bom_node = { bn.source_node_id: bn.id | 该范围拆解主表 }
welding_by_bom_node   = { bd.source_node_id: fee
                          | fee.source_breakdown_node_id = bd.id
                          | 该范围年+基地+车型+BOM版本 }
本卡 welding = welding_by_bom_node.get(R.id)   // 仅 R，不含子孙
```

不要用 `fee.level` 分支去「给树根改抄 L1」。`fee.level` 应等于 `R.level`，不等则记 `calc_message` 警告，仍用该行金额。

| 有无行 | 金额 | partial |
|--------|------|---------|
| 有，且该行 `calc_status` 为 ok | 抄 `final_welding_fee`（空则 `total_welding_fee`）和 `other_fee` | 否 |
| 有，且缺单价 / partial / failed | 仍抄能抄的金额 | **是** |
| 无行 | 0 | **否**（P7） |

分总成卡抄分总成自己的行，给采购看；与树根那一笔 **并存、禁止相加**。

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

一次落地、不双写。现网表：

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

| 字段 | 说明 |
|------|------|
| `detail_text` | 全过程文本（范围、上游价表、每张卡一行、汇总） |
| `detail_json` | 每张卡摘要 JSON（状态、金额、缺叶），供报告页筛选；列表接口不解析 |

`GET /api/costing/assembly-costs/calc/logs/{id}` 返回 `detail_text` + `cards`。计算历史点「过程」打开独立页 `/assembly-cost-calc-report?log_id=`（浅色报告，可按状态 / 层级 / 树根 / 零件号筛选；可导出当前筛选或全部核价卡 Excel）。实现落在 `assembly_cost/calc_report`（脚本 `features/costing/assembly-cost/calc-report/boot.js`），对外 URL 不变。

`GET /api/costing/assembly-costs/calc/logs/{id}/export-download` 导出同口径工作簿（封面摘要 / 核价卡 / 过程说明），查询参数 `keyword`、`status`、`level`、`tree_root` 与报告页筛选一致。

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
  提交、写日志终态（含 detail_text / detail_json）、释放锁
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

Ready VO 增加：`subject_count`、`tree_root_count`、`procurement_object_count`、`welding_fee_count`（**当前树拆解对齐的费行**，不含旧 id / 孤儿行）、`welding_fee_level_counts`（同上口径）、`stamping_complete`、`stamping_incomplete_suppliers`、`welding_calc_complete`。保留 `l0_count` 一期别名 = `tree_root_count`（避免旧前端崩），随后删除。计算页芯片与 P20 同一套覆盖；未就绪黄条展示 `message`，禁止只数范围内存量行却把按钮关掉。

缺清单：警告「采购对象未生成，本趟只出装配∪树根」（不挡计算）。年度价/包装为 0：黄灯，不挡。

---

## 10. API / 权限 / 页面

### 10.1 路径

产品入口：

| 类型 | 路径 |
|------|------|
| API | `/api/costing/assembly-costs` |
| 计算页 | `#/assembly-cost-calc` |
| 一览页 | `#/assembly-cost` |
| 侧栏 | 「总成核价」（计算 / 一览） |

任务类型：`assembly_cost_calc`。引擎阶段 id：`assembly`。

### 10.2 JSON 接口（仍 `ApiResponse[T]`）

现网计算/列表/详情/批量审删/导出/筛选年 **能力保留**。前缀 `/api/costing/assembly-costs`。

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

### 10.3 权限

`catalog.json` → `Perm.*`；前端 `can()` 用同一码。不要在 `permission-design.md` 再抄一棵树。不新增第二组「应成本」菜单。

| 码 | 用途 |
|------|------|
| `menu:assembly-cost-group` | 侧栏分组 |
| `menu:assembly-cost-calc` / `op:assembly-cost-calc:view\|run\|delete` | 计算页 |
| `menu:assembly-cost` / `op:assembly-cost:view\|delete\|approve\|reverse\|export` | 一览页 |

### 10.4 前端

目录：`static/js/features/costing/assembly-cost/{calc,list}/`。`?v=` 递增。`index.html` 侧栏 `data-page`。`pageMeta` 标题「总成核价计算 / 总成核价一览」。

一览：

- 默认 `view=finance`，表头仍偏总费用 / 间接（现网 HUD）。  
- 切换采购：列为材料成本、焊接费/电泳黑漆等（数据仍 `welding_amount`）、**总成本**（关注列=`total_amount`）、对象种类中文、确认状态；不展示报价/价差、不展示 I3～I8。  
- 操作仍只在操作列。  
- 有子件树根不出现在采购视图。  
- 单卡**成本还原报告**见 [assembly-cost-restore-design.md](assembly-cost-restore-design.md)：一览点「还原」打开**新页签画册级静态报告**（浅底、封面+章扉、禁止黑底与页内交互）。

计算页：就绪展示树根数 / 主体数 / 清单对象数 / 各层焊接行数。开始计算 = 全卡（不在页面默认勾 `levels=[0]`）。计算历史「过程」新页签打开浅色报告（非主应用黑底）。

导出（P22，入口随视图，权限仍 `op:assembly-cost:export`）：

- **财务视图：**「导出总成核价」→ `GET /api/costing/assembly-costs/export-download?view=finance`（一览 + 材料 + 焊费按卡 `welding_fee_id` + 间接）。成品核价一览表头写本表合计（条数、核算正常数、材料/焊接/月总账/间接/总费用）；末行 `SUM` 不进筛选。合计是当前导出范围内的树根。「导出核对合册」→ `GET /api/costing/monthly-bundle/export-download`（**无** `view`，成品块只树根，再叠冲压核价 / 加工费 / 钢材 / 年度价 / 包装 / 焊价）。
- **采购视图：**只「导出零件成本」→ `export-download?view=procurement`。文件名 `零件成本_2025年12月_青岛_T2AA_…xlsx`。Sheet：成本一览 / 材料明细 / 焊接费。成本一览表头写本册对象合计（件数、核算正常数、材料/焊接/总成本）；末行 `SUM` 不进筛选、不随筛选变化。合计是对象卡全量，不是整车月总账。

---

## 11. 现网符号索引

| 区域 | 符号 |
|------|------|
| 包 | `app/services/costing/assembly_cost/**`、`app/routers/costing/assembly_cost/**`、`app/repositories/costing/assembly_cost/**` |
| 模型 / schema | `AssemblyCost*`、`assembly_cost_{dto,vo}` |
| 表 | `costing_assembly_costs` / `_items` / `_indirects` / `_calc_logs` |
| 引擎 | 零件价完成且 **焊接费覆盖全部要抄的 level** 才跑 assembly（P20）。补焊 **禁止** 只传 `levels=[0]`。阶段 id `assembly`；焊接费阶段 `annual_welding_fee`。本切片不得内部触发上游 |
| 合册 | `monthly_bundle_export_service` → 树根过滤 |
| LLM | `menu_catalog`、`field_labels`、`cost_analysis/`（查现表 `costing_assembly_costs`） |
| 权限 / 种子 | `catalog.json` → `codes.py`（§10.3） |
| 前端 | `index.html`、`app.js`、`features/index.js`、`static/js/features/costing/assembly-cost/` |
| 测试适配 | `tests/costing/l0_assembly_sim.py`（领域 L0 树根金样，公式委托 `rollup_assembly`） |
| 任务常量 | `TASK_TYPE_ASSEMBLY_COST_CALC`（`assembly_cost_calc`） |

焊接费切片、采购对象清单切片 **不改公式**。costing 只读它们。

---

## 12. 验收

| 项 | 口径 |
|----|------|
| 青岛 T28 2025-01 有子件树根 | 与现网 `l0_assembly_sim` 分项金额一致 |
| 青岛退化树根 | **允许与旧模拟不同**（现网材料 0 → 现当叶子）；单独列 diff |
| 4 层夹具 | 递归、中间层一口价剪枝、子卡打开子树 |
| 同号两支 | 两张卡或两行明细，金额相加；焊接按节点不撞号 |
| T13J 芜湖 2026-01 `D/09` | 整理后：P20 可开算；卡数 **97**（无清单）或生成清单后 **229**；53 张分总成卡应对 53 行 L1 焊接费；14 张退化卡材料非 0；7 条年度价均为叶子，无一口价剪枝；包装 0 |
| 恒等式 | persist 前每卡检查 |
| 合册 | 行数 = 树根数，不是 229；API 无 `view` |
| 采购应成本册 | 行数 = 对象卡数；无间接 Sheet；焊费按卡 `welding_fee_id` |

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
| 树根 ④⑤ 只抄树根自己的焊费行 | 用下级焊接费滚动进 L0 / 用 L1 旁证总成焊信 |

---

## 15. 相关文档

| 文档 | 角色 |
|------|------|
| [l0-assembly-costing-design.md](l0-assembly-costing-design.md) | 冻结史料：原五块积木、I1～I8、青岛样例 |
| [l1-assembly-costing-design.md](l1-assembly-costing-design.md) | 应成本口径；§7 委外表 **作废** |
| [welding-fee-design.md](../bom/welding-fee-design.md) | 按节点工费 |
| [bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md) | 集合 C |
| [bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md) | 合同对方（供应商第二期已落地）；本切片不存 |
| [procurement-contract-report-design.md](procurement-contract-report-design.md) | 签约横表只读 `should_cost`（已落地）；点「计算过程」不改本页 |
| [assembly-cost-restore-design.md](assembly-cost-restore-design.md) | 计算过程画册（已落地） |
| [assembly-cost-restore-ledger-display-design.md](assembly-cost-restore-ledger-display-design.md) | 计算过程：总成（商务）vs 采购对象（采购）展示（已落地） |
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
| 2026-09-01 | **P21：** 树根卡焊接口径与现网 L0 相同，禁止下级焊接费上滚；焊信在总成格已是整台汇总，下级不能旁证。 |
| 2026-09-01 | 计算过程：`detail_text`/`detail_json` 落库；独立浅色报告页可筛选。 |
| 2026-09-05 | **P22：** 导出分册。合册只树根、API 无 `view`；采购单独应成本册（无间接、无合册价表）。 |
| 2026-09-05 | 采购导出须锁年度/月份/基地/项目/版本；表内去重这五列；材料明细佐证合并。 |
| 2026-09-05 | 采购应成本一览不展示报价/价差：核算参考，不参与采购业务。 |
| 2026-09-05 | 采购一览金额列：材料成本、焊接费/电泳黑漆等（数据=焊接费）、总成本（关注列）。 |
| 2026-09-05 | 采购导出文件名「零件成本」、表页「成本一览 / 材料明细 / 焊接费」。 |
| 2026-09-05 | 采购成本一览：表头本册对象合计 + 表外 SUM；不进筛选。 |
| 2026-09-05 | 成品核价一览同样：表头本表合计 + 表外 SUM；不进筛选。 |
| 2026-09-09 | P20：无冲压工艺不判零件价完成；无 BOM 不判焊接、总成不开始。 |
| 2026-09-11 | 计算过程报告：分总成节点不得把兄弟卡焊装画进成品账材料行；协议页不改。见 restore-ledger-display。 |
| 2026-09-14 | **P4：** 外购件总成（卡根有子件且命中年度价）本卡用年度价，子孙已含不报缺价，本卡不抄焊接。 |
