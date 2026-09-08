# BOM 年度零件价表 — 单表设计

> **状态：已上线。** 外购价与 L1 一口价合并为同一张表、同一套上传/列表/审核。  
> **产品入口：** `#/bom-annual-part-price-upload`、`#/bom-annual-part-price`；API `/api/bom/annual-part-price`。  
> 成品月核价总览见 [l0-assembly-costing-design.md](../costing/l0-assembly-costing-design.md)。  
> 分层与切片硬规则见 [architecture.md](../architecture.md)。

---

## 1. 为什么合成一张表

| 维度 | 两张表 | **一张表** |
|------|--------|------------|
| 用户操作 | 两套 Excel、两个菜单、两次审核 | **一次导入、一个列表** |
| 用户心智 | 「外购」vs「一口价」两套概念 | 「这个零件今年在这个基地多少钱」 |
| 唯一键 | 两边都是 `(location, year, part_number)` | 完全相同，天然可并 |
| 金额字段 | `unit_price` / `bundle_unit_price` | **统一 `unit_price`** |
| 核价语义差异 | 靠「进哪张表」区分 | **靠 BOM 节点形态区分**（见 §4） |

**写死：** 价表只回答「有没有价、单价多少」；  
「算成外购叶子」还是「算成 L1 包价并剪枝」由 **核价遍历时看 BOM** 决定，不在价表上再拆表、也不需要 `pricing_mode`。

---

## 2. 定稿约定

| 约定 | 内容 |
|------|------|
| 表名 | **`bom_annual_part_prices`**（BOM 年度零件价） |
| 归属 | **`bom`** 切片（上游主数据） |
| 节奏 | 一基地、一年订一次 |
| 车型 | **不要** `vehicle_model` |
| 唯一键 | `(location, year, part_number)` |
| 取价 | 只认 `location + year + part_number` |
| 维护 | 一套 Excel 上传 + 列表只读 + 审核（对齐焊接单价） |
| 不作 | 不按外购/一口价拆表；不用英文 `category`；规格不进唯一键 |

---

## 3. 垂直切片

```text
bom（一张价表：上传 / 列表 / 审核 / 导出）
  ↑ 只读
costing（成品月总账编排）
```

```text
app/…/bom/annual_part_price*
static/js/features/bom/annual-part-price/{upload,list}/
```

侧栏：**焊接工程 → 采购对象 → 年度零件价**（上传 / 列表）。下载模板按 **基地 + 项目**：采购对象 `other_leaf`（标准件/胶等）∪ 该项目 BOM 无子件且 **不在该项目工艺库** 的叶子（含未进工艺的 L2 板料）。有子件的分总成不进模板。不要拆成「外购价」「分总成价」两个入口。

导入模板 Excel 排版见 [annual-part-price-import-template-design.md](annual-part-price-import-template-design.md)（`template_builder.py`：只写出、不查库）。

---

## 4. 核价时怎么用这一行价（关键）

```text
取价：location + year + part_number
命中价表后，看当前 BOM 节点：

  ① 节点是 L1 且【有子节点】
       → 按一口价：unit_price × 用量
       → 停止对该 L1 下所有 L2 做成本 rollup

  ② 节点是叶子，且当月冲压价表无该零件号
       → 按外购：unit_price × 用量

  ③ 叶子零件号命中当月 stamping_part_costs
       → 走冲压零件价（不看 BOM 是否 make/有料厚）

  ④ L1 有子节点但【价表无记录】
       → 向下拆 L2 分别取价
```

| 价表有没有行 | BOM 上是什么 | 结果 |
|--------------|--------------|------|
| 有 | L1 + 有子件 | 一口价，子树跳过 |
| 有 | 叶子且当月冲压价未命中 | 外购计入 |
| 无 | L1 + 有子件 | 拆散 L2 |
| 无 | 叶子 | 走当月冲压价；都没有则 missing |

> 用户不必理解「我该导进哪张表」——只要零件号 + 单价进这一张表即可。  
> 若把「有子件的 L1」的价导进来，核价自动当一口价；若是螺栓/胶块，自动当外购。

---

## 5. 表结构：`bom_annual_part_prices`

### 5.1 生产导入列（与现网样例对齐）

| Excel 列 | 字段 | 必填 | 样例 |
|----------|------|------|------|
| 基地 | `location` | ✓ | 青岛 |
| 年度 | `year` | ✓ | 2025 |
| 零件号 | `part_number` | ✓ | QR36410 / 501004437AA / TBD |
| 零件名称 | `part_name` | | 焊接方螺母 |
| 规格 | `specification` | | 展示/当档，不取价；可从 BOM `thickness_text` 预填 |
| 采购单位 | `purchase_unit` | | 报价包装单位，如打、瓶；同核价可空 |
| 采购单价 | `purchase_unit_price` | | 元/采购单位；空=未报采购价 |
| 转换系数 | `conversion_factor` | | 正整数，默认 **1**；1 采购单位 = N 核价单位；核价单价 = 采购单价 ÷ 系数 |
| 单位 | `unit` | ✓ | **核价单位**，默认 `pcs`，应对齐 BOM `qty_unit` |
| 单价 | `unit_price` | ✓ | **核价单价**；`2.13`；**允许 0** |
| 原供货类型 | `supply_type` | ✓ | `沿用` / `标准件` / `胶块`；一口价行可用 `分总成` / `一口价` |
| 供应商 | `supplier_name` | | 常空；档案，导入不门禁（§5.4） |
| 备注 | `remark` | | 常空 |

### 5.2 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | |
| `location` | String(50) | ✓ | 采购基地 |
| `year` | Integer | ✓ | 定价年度 |
| `part_number` | String(50) | ✓ | 取价主键（允许 `TBD`） |
| `part_name` | String(200) | | 展示 / 核对 |
| `specification` | String(100) | | 规格，展示；**不参与取价** |
| `purchase_unit` | String(20) | | 采购单位 |
| `purchase_unit_price` | Numeric(12,4) | | 采购单价 |
| `conversion_factor` | Integer | ✓ | 正整数，默认 1；`unit_price = purchase_unit_price / conversion_factor` |
| `unit` | String(20) | ✓ | **核价单位**，默认 `pcs` |
| `unit_price` | Numeric(12,4) | ✓ | **核价单价**（外购与一口价共用；核算读这一列） |
| `supply_type` | String(50) | ✓ | 原供货类型原文 |
| `supplier_name` | String(100) | | 报价档案，可空。**不是**合同对方，**不**跑供应商 `require_enabled`。见 §5.4 |
| `remark` | Text | | |
| 审核字段 | | ✓ | 同 `bom_welding_unit_price` |
| AuditUserMixin | | ✓ | |

**不建：** `bundle_unit_price`、`pricing_mode`、英文 `category`、`vehicle_model`、`month`。规格用 `specification` 展示，不把 BOM `thickness_text` 当取价键。

### 5.3 约束与审核

```text
UNIQUE (location, year, part_number)
Index: (location, year), part_number, supply_type, audit_status
```

`approved` 禁止改 / 删 / 导入覆盖；须先反审核。

### 5.4 供应商列（报价档案，不是写门禁）

对齐 [supplier-design.md](../masterdata/supplier-design.md) **S15**。本列给总成核价抄 `vendor_name`，**不是**采购对象合同对方，**不是**工艺冲压工厂。

| 路径 | 行为 |
|------|------|
| Excel 导入 | 可空。非空按 Parser `strip` **原样入库**。**不**调用 `SupplierService.require_enabled`。对不上主数据 **不**整单失败、**不**代建供应商。这是供应商 S5「点选禁止自由输入」的 **例外** |
| 列表手工编辑 | 控件改为下拉：空 + `list_enabled()`；展示「缩写（全称）」；`value = 全称`。**禁止**文本框自由打字。选空 = 清空。已审核须先反审核 |
| 行上已有乱写 / 已禁用全称 | 打开编辑时保留当前值（额外 option），不要一打开就清空。用户可改成下拉里的厂或改成空 |
| 核算 | 命中价表则 `vendor_name = supplier_name`（行上字符串）。缺供应商或乱写 **不挡算** |

禁止：把本列当供应商建档入口；用本列顶替采购对象 `supplier_name`；导入接工艺那套硬停。

---

## 6. 与旧两表方案对照（已废弃）

| 旧方案 | 新方案 |
|--------|--------|
| `bom_purchased_part_prices` | 并入本表 |
| `bom_sub_assembly_prices` | 并入本表 |
| 两套前端 upload/list | **一套** `annual-part-price` |
| 核价读两张表 | 核价只读 **一张** |

已落地的旧 Model / Router / 前端若存在，落地本设计时 **删掉或迁到本表**，勿双轨并存。

---

## 7. 评审清单

- [ ] 同意 **一张表** `bom_annual_part_prices`，一套上传/列表
- [ ] 同意核价语义由 **BOM 节点形态** 决定（有子件 L1 = 一口价剪枝；叶子 = 外购）
- [ ] 同意唯一键 `(location, year, part_number)`，无车型
- [ ] 同意导入列：基地 / 年 / 零件号 / 名称 / 单位 / 单价 / 原供货类型
- [ ] 同意单价允许 0；审核对齐焊接单价

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-20 | 初稿（两表） |
| 2026-08-20 | 按生产样例去掉 thickness_text / 英文 category，加 supply_type |
| 2026-08-20 | **合并为单表** `bom_annual_part_prices`：外购与 L1 一口价共用；语义靠 BOM 节点区分 |
| 2026-09-01 | 导入模板按基地+年度下载；零件来自采购对象「标准件/胶等」；侧栏排在采购对象之下 |
| 2026-09-02 | 抽出 `template_builder`：导入模板写出与 Import Service 取数分离；见导入模板设计说明 |
| 2026-09-02 | 模板行源改为 BOM 外购叶子（对齐总成核价叶子取价），不再只取采购对象 `other_leaf` |
| 2026-09-02 | 模板按基地+项目；行源 = 采购对象 other_leaf ∪ BOM 叶子且不在本项目工艺库；不以 make/料厚排除 |
| 2026-09-08 | §5.4：`supplier_name` 是报价档案（供应商 S15）。导入不门禁；列表编辑改下拉、可空。Excel 是点选禁自由输入的例外 |
| 2026-09-08 | 加规格 / 采购单位 / 采购单价 / 转换系数；`unit`/`unit_price` 为核价口径 |
| 2026-09-08 | 转换系数改为正整数；核价单价 = 采购单价 ÷ 系数（1 打=12 个则填 12） |
