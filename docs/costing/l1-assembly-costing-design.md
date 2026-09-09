# 委外分总成应成本 — 设计说明

> **后续设计已合并：** 不再单开委外表 / 第二套引擎。与成品月总账合并为 [assembly-costing-design.md](assembly-costing-design.md)（换根打开子树；采购读 `should_cost`）。§7 结果表方案 **作废**。本文保留应成本口径与防双计讨论。  
> **状态：草案（未实施）。本文只定口径，不改代码。**  
> 切片：**`costing`**。只读采购对象清单、焊接拆解、冲压零件价、年度零件价、焊接单价。  
> 采购对象集合：[bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md)。本文不扫树认人。  
> 财务成品账：[l0-assembly-costing-design.md](l0-assembly-costing-design.md)。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)。

---

## 0. 一句话

**清单定集合，核价定公式。** 对采购对象清单算出「应成本」，用来和二级签合同。有子件的 L0 继续走现网成品月总账，给财务，不对二级开总成合同。

| 账 | 对象 | 部门 | 现网 |
|----|------|------|------|
| 财务核算账 | 有子件的 L0 | 财务：核算成本，将来对实际 | 已有成品月总账 |
| 采购应成本账 | 清单里的三类采购对象（默认再叠加「确认外发」） | 采购：应成本 vs 二级报价 | **缺口** |

奇瑞只认一级交出的供货总成；总成不得整层委外（电泳等处理除外）。二级只接分总成和冲压件。因此 **禁止** 对带内部号一级件的 L0 做「整层应成本对二级报价」。采购对象清单已保证这类 L0 不列入；全部 L1 无内部号的 L0 按退化供货件列入。

---

## 1. 两本账各算什么

产能不够时，交给二级的是 **直接采购**（买焊好的分总成，或买冲好的板），不是买散件回来自己做。

```text
财务 ── L0 供货总成核算成本 ──将来──► 对实际，出差异
采购 ── 采购对象清单上的应成本 ──现在──► 和二级签合同
```

| 清单 `object_kind` | 应成本口径 |
|--------------------|------------|
| `l1_subassembly` | Σ L2 冲压或外购 + 该 L1 自己的工艺费 |
| `l1_stamping` | 该件冲压价；无工艺行 |
| `l0_degenerate` + `special_process` | 自身冲压 + 电泳等处理费 |
| `l0_degenerate` + `stamping_blank` | 仅自身冲压；不编电泳 |

L2 只作为分总成的材料叶子。L1 其它叶子（清单核对区）默认不算冲压应成本。

自制还是外发由清单行上的确认回答。**合同口径** = 采购对象行 ∩ 确认外发。未确认前可以按采购对象出候选应成本便于对表，列表上须能区分。

---

## 2. 现网缺什么

焊接拆解已经扫 L0+L1。焊接费表 `bom_welding_fees` 按节点 `level` 计费。应成本工艺费读 **`level=1`**（见 [welding-fee-design.md](../bom/welding-fee-design.md)）。

成品月核价：有子件的 L1 命中年度价就一口价剪枝；**L0 自身不当叶子**。退化 L0 的月总账材料为 0，只剩可能拆失败的焊接费。

| # | 缺口 | 对采购账的影响 |
|---|------|----------------|
| G1 | 委外加工费无独立结果 | L1 凸焊含在 L0 焊接费里，对不上二级 |
| G2 | 一口价挡住应成本 | 财务走包价是对的；采购要把子树打开 |
| G3 | 退化 L0 不算冲压 | 采购/财务都缺材料 |
| G4 | 退化 L0 材料属性落不到 L0 | 钢厂/料厚空，冲压对不上 |
| G5 | 材料清单无二级厂名 | `材料厂家` 是钢厂/紧固件商，不是分总成厂 |
| G6 | ~~`电泳黑漆：0.098m2` 拆不出~~ | Parser 已按电泳面积；**重跑拆解**后计费 |
| G7 | ~~`凸焊:：2` 未拆~~ | Parser 已压连续冒号；**重跑拆解**后计费 |
| G8 | 备注盐雾 720h 无映射 | 仍按 ≤244H |

G4 / G6 / G7 是算账前置：名单可以先抽出，工艺量和材料不齐则 `partial`。

---

## 3. 采购应成本公式

取价与成品侧一致：冲压键 = 年 + 月 + 基地 + 项目 + 零件号；工艺单价 = `bom_welding_unit_price`（基地 + 年 + 标准工艺名）。

**分总成 `l1_subassembly`**

```text
stamping_amount  = Σ (L2 命中当月冲压 unit_cost × 相对该 L1 的有效用量)
purchased_amount = Σ (L2 未命中冲压、命中年度价)
process_fee      = Σ (该 L1 拆解明细 × 焊接单价)   // 不认 L0 原文
should_cost      = stamping_amount + purchased_amount + process_fee
vendor_quote     = 年度价 unit_price × L1 用量     // 可空
gap              = vendor_quote - should_cost      // 无报价则只出应成本
```

**L1 冲压件 `l1_stamping`**

```text
stamping_amount = 该 L1 当月冲压 unit_cost × 用量
process_fee     = 0
should_cost     = stamping_amount
vendor_quote    = 年度价 × 用量                    // 可空
```

无冲压价 → `partial`。不要因为无子件就当标准件跳过冲压口径。

**退化 L0 `l0_degenerate`**

```text
stamping_amount = 该 L0 零件号当月冲压 unit_cost × 单车用量
process_fee     = special_process 时：拆出的电泳/面积等 × 单价
                = stamping_blank 时：0
should_cost     = stamping_amount + process_fee
```

`stamping_blank` 按冲压件，不是总成委外，也不编电泳。财务侧退化 L0 材料仍为 0，要不要改成品 rollup 见 §8.2。

---

## 4. 财务账保持现网，防双计

成品月总账继续只给财务：

- 委外分总成有年度价 → 一口价，L2 不进财务冲压合计。
- 委外 L1 冲压件有年度价 → 财务按叶子取价；采购另出冲压应成本卡合同。
- L0 焊接费只挂 L0 原文。已 `rolled_in_parent` 的 L1 凸焊不要再加进 L0。
- 委外 `process_fee` **不要** 累进同一条 `welding_amount`。

| 场景 | 财务核算账 | 采购应成本账 |
|------|------------|--------------|
| 分总成有一口价 | 只进 bundle | 打开子树算应成本，**对比**一口价 |
| L1 冲压件 | 叶子进材料 | 另出冲压应成本；不要和财务材料加总成「付两遍」 |
| 分总成无一口价 | 现网拆 L2 进材料 | 补 L1 工艺费；材料不要和财务再加总到同一张应付 |
| L1 工艺已 rolled_in_parent | L0 焊接费已含 | 该行若确认外发，用 L1 自己的工艺，不要再加 L0 同名 token |
| 退化 L0 电泳 | L0 焊接费（拆得出才有） | 同一笔工艺用来配冲压、签合同，不要复制进月总账 |

---

## 5. 二级厂名

材料清单 **没有** 供应商列。

| 字段 | 能当二级厂名吗 |
|------|----------------|
| `material_mill`（材料厂家） | 不能 |
| 备注 | 只有经营话术 |
| 年度价 `supplier_name` | 仅展示，可作候选 |

一期：能挂年度价供应商就挂，空着不算失败。不要从材料厂家猜。导入最多提示，不拦上传。

---

## 6. 拆解与 Parser（计费前置，不是新产品）

| 项 | 口径 |
|----|------|
| 拆解生成范围 | 保持 L0+L1 |
| 委外工艺行 | 读 `bom_welding_fees` 且 `level=1`（年结果）；退化 L0 特殊工艺读 `level=0`。未迁表前可按拆解明细 × 单价临算 |
| Parser | 补 G6 / G7；盐雾 720h 见 §8.3 |
| 列表 | 应成本按 `object_kind` 筛；确认外发另列。不要在拆解列表里再认人 |

---

## 7. 结果表（未建）

财务仍只读焊接费 **`level=0`**。应成本工艺费读 **`level=1`**，不要把子层加进成品 `welding_amount`。另开：

```text
costing_outsourced_assembly_costs          1 个委外单元 × 年/月
 ├── costing_outsourced_assembly_items     材料叶子
 └── costing_outsourced_assembly_processes 可拷焊接费明细（对账；金额引用年结果）
```

唯一键：`(year, month, location, vehicle_model, bom_version, part_number, source_node_id)`。  
同一零件号可在多棵树上出现，必须带 `source_node_id`。

| 字段 | 说明 |
|------|------|
| `node_kind` | 抄清单 `object_kind`；退化 L0 另存 `degenerate_subtype`。禁止 `l0_outsourced_assembly` |
| `vendor_name` | 可空 |
| `stamping_amount` / `purchased_amount` / `process_fee` / `should_cost` | §3 |
| `vendor_quote` / `gap_amount` | 无报价则空，不因此 failed |
| `calc_status` | `ok` / `partial` |
| 审核 | 与现网结果表同构；已审禁止覆盖 |

前端：核价下「委外应成本」计算 / 一览，不要塞进 L0 焊接费列表。

`costing` 组合上游；`bom` / `stamping` 不得反向依赖。

---

## 8. 待拍板（只留算账）

### 8.1 算哪些行

| 方案 | 做法 |
|------|------|
| 确认后才算（推荐合同口径） | 只吃采购对象 `confirm_status = outsourced` |
| 先算全集再筛 | 主表每行都出应成本，确认后才当合同 |
| 有年度价才算 | **否决**：没导价的外发件会漏；年度价不当认人 |

未确认前允许出候选应成本。不要因没供应商导入失败。

### 8.2 退化 L0 冲压进不进财务核算账

现在成品材料为 0，财务对实际会对空。推荐 **改 `rollup_l0`：无子件 L0 自身当叶子**，与采购应成本同一套冲压数，单独验收，不和采购账绑死。

### 8.3 盐雾 720h

备注写明升档。自动映射 `电泳（盐雾试验要求244H-720H）`，还是默认 ≤244H 留人工改。

### 8.4 工艺单价

一期复用基地年焊接单价，不按供应商另建价表。

---

## 9. 落地顺序

```text
P0  采购对象清单 P0/P1 完成（检测通过，可确认）
P1  Parser：G4 / G6 / G7；拆解重跑，工艺行齐全
P2  应成本计算（只读采购对象清单 + 上游价）；默认确认外发，可出候选
P3  财务退化 L0 是否当叶子（§8.2），单独评审
P4  挂年度价 supplier_name；不改材料清单模板
```

P3 不和 P2 绑死。

---

## 10. 做 / 不做

| 做 | 不做 |
|----|------|
| 对采购对象清单算应成本 | 再扫 BOM 树认人 |
| 打开分总成 L2、给冲压件/退化 L0 取冲压价 | 对有子件的 L0 开二级总成合同 |
| 应成本 vs 一口价给采购签合同 | 改造成另一套 L0 成品核价 |
| 财务仍用现网 L0 月总账 | 本期做实际成本 / ERP 对账 |
| 只读采购对象清单、拆解、冲压价、焊接单价、年度价 | 在 `bom` 切片写核价编排 |
| Parser 修已出现的原文 | 新建第三套焊接拆解 |

---

## 11. 相关代码与文档

| 位置 | 角色 |
|------|------|
| [bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md) | 采购对象清单、确认列 |
| [l0-assembly-costing-design.md](l0-assembly-costing-design.md) | 财务 L0 月总账 |
| [bom-annual-part-prices-design.md](../bom/bom-annual-part-prices-design.md) | 一口价 / `supplier_name` |
| [welding-process-breakdown-design.md](../bom/welding-process-breakdown-design.md) | 有原文即拆（含分总成）；应成本读 L1 行 |
| [welding-fee-design.md](../bom/welding-fee-design.md) | 焊接费一表 + `level`；应成本工艺费读 **level=1** |
| `app/services/costing/l0_assembly_cost/calc/rollup.py` | 一口价剪枝；L0 不当叶子 |
| `app/parsers/bom/node_parser.py` | 材料不落到 L0（G4） |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-28 | 初稿：两本账、主机厂约束、应成本、待拍板。 |
| 2026-08-28 | L1 冲压件与分总成并列；叶子不能全当自制。 |
| 2026-08-31 | 认人迁到采购对象清单；本文只算应成本。 |
| 2026-08-31 | 按下游文档收口：输入、公式、防双计、拍板；树计数与分类不再复述。 |
| 2026-08-31 | 对齐清单定集合：对象来自采购对象清单，字段 `object_kind`。 |
| 2026-08-31 | 相关文档改为成品焊接费设计说明。 |
| 2026-08-31 | 相关文档改为焊接工艺拆解设计说明。 |
| 2026-08-31 | 工艺费对齐焊接费一表 + `level`（代码未迁）。 |
