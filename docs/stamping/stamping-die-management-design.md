# 冲压件模具管理 — 设计说明

> **状态：已落地（只入库布点几何与分摊比例；本切片不算金额）。**  
> 样本：`excel_sample/T13J/副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx`（Sheet「零件汇总」）。  
> 业务列 A～AC；模板可在套数后插入「模具编号」列。AD 及以后（责任人、模具款、检具款等）一律忽略。检具费档案另表，见 [stamping-gauge-fee-design.md](stamping-gauge-fee-design.md)，**不读布点 AD+ 检具款列**。  
> **导入顺序**：先布点后工艺、编号出自布点或缺号按 `DP-40-{项目}-流水` 补、布点不认供应商，见 [stamping-apqp-die-before-process-design.md](stamping-apqp-die-before-process-design.md)。  
> 有效期现网改造（布点零件行生失效、停整项目覆盖）见 [bom-process-die-effective-period-design.md](../engineering-change/bom-process-die-effective-period-design.md)。  
> **冲压模具费**是本表直接下一跳：`stamping_die_fees.source_die_part_id` → `stamping_die_parts.id`（`RESTRICT`）。有模具费则不能删布点，文案「仍被冲压模具费引用，请先删除对应模具费后再删」。各序 `source_die_process_id` 不加 FK（再导会删插工序）。金额在 [stamping-die-fee-design.md](stamping-die-fee-design.md)；引擎补算见 [costing-engine-design.md](../costing/costing-engine-design.md) §5.2。  
> 关联：现网冲压工艺导入（`app/parsers/stamping/`、`part/upload/cost_ratio_resolver.py`）、成品间接费 I7/I8 预留（[assembly-costing-design.md](../costing/assembly-costing-design.md)）。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)。

---

## 0. 一句话

**本模块是计算模具费用的依据。** 把「冲压模具布点工艺清单」按零件主表 + 工序子表入库：重量、尺寸、共模比例，给后续模具费计算用。  
对照现网：冲压工艺确认表是 **加工费** 与 **零件材料（含是否利废）** 的依据，见 [stamping-process-confirmation-design.md](stamping-process-confirmation-design.md)；本表是 **模具费** 的依据。两套不要混、也不把布点回写进 `stamping_parts`。家模副产品由工艺表四列全空判定，**禁止**用布点空板料改零件利废标，见 [stamping-family-die-byproduct-design.md](stamping-family-die-byproduct-design.md)。  
上传形态对齐工艺导入（异步解析、覆盖写入），关注模具字段，**不管理零件简图**。  
上传必须选择 **采购基地**，再选该月可引入项目（下拉，不是手填）。子表 **分摊比例**（左右共模对半，**不做级进 0.80**）。本切片只落模具本身（重量、尺寸、工序、比例），**不算金额**，也 **不记寿命/是否还摊**。金额由年度模具费计算 / 核价引擎读本表算出；满 10 万件是否还摊由费用切片判定，不进本表。单价政策见 [stamping-die-unit-price-design.md](stamping-die-unit-price-design.md)。冲压件检具费见 [stamping-gauge-fee-design.md](stamping-gauge-fee-design.md)。

---

## 1. 本切片只管模具本身

本表存的是 **项目模具布点**（零件、工序、尺寸、共模比例），不是模具费生命周期。

**不在主表打「待分摊 / 不用分摊」。** 满 10 万件、多项目共用已摊完等，属于后续 **模具费计算层** 的判定，与本件模具几何/工艺属性无关，本期不建字段、列表也不做这类统计。

子表 `alloc_ratio` 仍要：它描述的是 **共模时本件占几成**（左右件、一出二），是模具本身怎么布点的性质，不是寿命到没到。

| | 子表 `alloc_ratio` | 寿命 / 是否还摊 |
|--|-------------------|----------------|
| 回答 | 共模时本件占几成 | 后续计算层决定；**不进本表** |
| 典型 | 左右件各 0.50 | 跨项目累计 ≥ 10 万件则分摊额记 0（费用切片处理，不进本表） |

本切片 **不算金额、不自动累加多项目产量、主表无分摊状态列**。年度模具费 / 引擎必须读本表的重量 / 尺寸 / `alloc_ratio`；满寿规则写在费用切片，禁止在布点主数据上挂生命周期状态。

---

## 2. 为什么单独建表

| | 冲压工艺确认表（现网） | 模具布点清单（本模块） |
|--|------------------------|------------------------|
| **在核价里的角色** | **冲压加工费** 的计算依据 | **模具费用** 的计算依据 |
| 怎么用 | 吨位 × 冲次单价 × `cost_ratio` | 重量 / 尺寸 / `alloc_ratio` → 后续出模具分摊额 |
| 样本名 | `T13J项目冲压工艺确认表-…` | `T13J项目冲压模具布点工艺清单-…` |
| 工序比例 | `cost_ratio`：见工艺确认 §4（共模 ×0.50，级进再 ×0.80；多序 PRG 例外另计） | `alloc_ratio`：同样识别共模，**不用 0.80** |
| 特有列 | 成形方法、自动化、料片长宽、**模具编号（可选）** | 模具长宽高、掏空系数、预估重量、模具方式、生产方式、零件等级、端拾器；子表 `die_number` **Excel 有则保留，空则按规则补号** |
| 工厂维度 | 有 `stamping_supplier` | 本样本无供应商列；模具按 **基地 + 项目** 管 |

两套 Excel 零件号会重叠，但服务的计算不同。禁止「再解析一遍布点清单去改 `stamping_processes.cost_ratio`」；算模具费时也禁止绕过本表、拿工艺确认表的吨位去凑。

---

## 3. 样本事实（A～AC，本表不是猜测）

解析范围：列 A=1 … AC=29。工作表「零件汇总」。T13J 样本 **88 个零件、355 道工序**（同一零件工序号不得重复，重复则上传整单拒绝）。零件号列纵向合并（常见 7 行一件）。

### 3.1 表头结构（两级）

| 列 | 一级（约第 3～4 行） | 二级（约第 5 行） | 落库位置 |
|----|----------------------|-------------------|----------|
| A | 序号 | | 主表 `seq_no` |
| B | 产品信息 / 零件号 | | 主表 `part_number` |
| C | 零件名称 | | 主表 `part_name` |
| D | 简图 | | **不读、不入库。** 样本有 DISPIMG，本模块不抽图、不存 `sketch_url`；要看简图去冲压零件列表 |
| E | 材质 | | 主表 `material` |
| F | 料厚（mm） | | 主表 `thickness` |
| G | 净重（kg） | | 主表 `part_weight` |
| H / I | 预估板料尺寸 | 长 / 宽 | 主表 `sheet_length` / `sheet_width` |
| J | 板料形状 | | 主表 `sheet_shape` |
| K | 可制件数 | | 主表 `parts_per_sheet` |
| L | 预估单件材料消耗（KG） | | 主表 `material_consumption` |
| M | 预估单件材料利用率 | | 主表 `material_utilization`：**0～1 的 Decimal**（不是百分数 0～100）。Excel 若写成 65 / 65% 则 Parser 除以 100 再入库 |
| N / O / P | 预估工艺 | 工序名称 / 工序 / 套数 | 子表 `process_seq` / `process_code` / `die_sets` |
| Q / R / S | 预估模具尺寸 | 长度 / 宽度 / 高度 | 子表 `die_length` / `die_width` / `die_height` |
| T | 掏空系数 | | 子表 `hollow_factor`（工序行；零件行合并时填首道） |
| U | 预估重量（T） | | 子表 `estimated_weight_t` |
| V | 预估重量小计（T） | | 主表 `estimated_weight_subtotal_t` |
| W | 使用设备吨位（T） | | 子表 `tonnage` |
| X | 模具类型 | | 主表 `die_type`（钢板模 / 铸造模 / 单干） |
| Y | 模具方式 | | 主表 `die_method`（双槽 / 合并 / 一出二 / 单干…） |
| Z | 生产方式 | | 主表 `production_mode`（手工线 / 级进模 / 自动化…） |
| AA | 是否需要端拾器 | | 主表 `needs_end_effector`：**存 Excel 原文**（如「需要」/空），不是布尔、不另建枚举类型 |
| AB | 零件等级 | | 主表 `part_grade`（A/B/B+/C/D） |
| AC | 备注 | | 主表 `remark` |
| AD+ | **不读** | 责任人、模具款、检具款、总费用、30%预付 | 本阶段禁止入库 |

文件第 1 行样本里有 `AA=版本` / `AC=V0-01`：**Excel 列仍忽略，不从布点表头入库。** 供应商、版本从同一基地+项目的冲压工艺回填；不是覆盖键。

车型 / 项目：从文件名或标题短语「项目冲压模具布点工艺清单」前缀取出（样本为 **T13J**）。布点 Parser 只用模具清单标题短语，不复用工艺确认表 `HeaderResolver`。上传表单选中的项目必须与解析结果一致，否则拒绝（防止选 T13J 却传 T28 文件）。

### 3.2 本样本「模具方式 / 生产方式」分布

用于默认分摊比例，不是模具钢种：

| 字段 | 高频原文 |
|------|----------|
| 模具类型 X | 钢板模、铸造模（偶发「单干」） |
| 模具方式 Y | 双槽、合并、左右合并、左右双槽、一出二、单干 |
| 生产方式 Z | 手工线、**级进模**、自动化、自动线、Transfer |

**级进模写在「生产方式」，不写在「模具类型」。** 分摊识别要扫 **模具方式 + 生产方式**，不要拿「钢板模/铸造模」当共模信号。

---

## 4. 本期范围 / 明确不做

### 4.1 做

- 上传（基地 + 项目必选，选项来自冲压工艺）+ **下载模板** + 异步解析 + 文件溯源登记。落库的就是 **模具本身**（重量、尺寸、工序、共模比例）。
- 模具零件列表：**必须先选基地 + 项目才请求、才出数**；详情改子表比例；导出、按作用域删除同样必须已选这两项。
- **不允许单件删除**（没有 `DELETE /{id}`）。
- 子表默认 `alloc_ratio`；覆盖上传时沿用已改比例（按零件号 + 工序号）。

### 4.2 不做（本切片边界）

- **本切片不算模具费金额。** 金额在 [stamping-die-fee-design.md](stamping-die-fee-design.md)；核价引擎可 `annual_die_fee` 补算。零件价按号 lookup 最终费（缺档 0）。成品 I7/I8 间接费路径另议，不在本表写金额。输入必须是本表，不能再解析布点 Excel 算费。同目录费用样例 Excel 的 AG 模具款等不混进本 Parser。
- **不管理简图**：列 D 跳过；不抽嵌入图、不落 `sketch_url`、列表/详情不展示零件图。本模块是模具费依据，不是工艺卡出图。
- **不自动统计多项目累计产量、主表不记是否还摊**（无产量接口；满 10 万留给费用切片）。
- **Excel 不读版本列。** 表头 V0-01 丢掉。供应商、版本从冲压工艺回填，列表不筛这两维，上传表单仍只选基地+项目。
- **不允许单件删除。** 只按基地+项目整包删。

---

## 5. 上传与作用域

### 5.1 表单（对齐工艺上传，多一步「项目」）

| 步骤 | 控件 | 规则 |
|------|------|------|
| 1 | 采购基地 | **必选**。四基地：大连 / 芜湖 / 鄂尔多斯 / 青岛。 |
| 2 | 项目 | **必选，下拉。** 该基地墙钟月可引入名单。文件标题项目须与所选一致。 |
| 3 | 文件 | `.xlsx` / `.xls`，异步 `start_upload`。 |
| — | 下载模板 | **要做。** 按钮对齐工艺上传「下载模板」；表头含可空「模具编号」列。 |

**上传表单不选手动供应商、版本。** 作用域仍是 **基地 + 项目**；写入时这两列为空。

模板接口：`GET /api/stamping/die/template`（`StreamingResponse`，权限与上传页 view 或 upload 同码即可，实现时与工艺模板一致）。

校验（Service，失败 `BusinessException`）：

1. 基地、项目均非空（项目来自该月可引入下拉）。不要求工艺库已有该组合。
2. Parser 得到的 `vehicle_model` 与填写的项目一致（规范化后比较，用现网 `normalize_vehicle_model`）。
3. 解析列可含模板插入的「模具编号」；旧 A～AC 样本无该列表头仍可解析。表头「版本 / V0-01」不映射字段。
4. 同一零件的工序号不得重复（含 Excel 行号的失败文案）；在覆盖删除之前检查。
5. 不按零件号到工艺库取供应商+版本。主表 `stamping_supplier` / `version` 写空。
6. Excel 已填模具编号原样保留。有任一外形尺寸且号空 → Service 发 `DP-40-{项目}-NNN`；共模无外形保持空。占用号为本文件已填 ∪ 覆盖前库内匹配该规则的号。满 999 整单失败。
7. 以上在 **覆盖删除之前** 做完补号占用扫描；失败不改已有布点。
8. 该工序 **长、宽、高、掏空系数均有值** 且 **预估重量有值** 时：核对重量 = 长×宽×高×掏空×7.85÷10^9（mm、g/cm³ → 吨）。相对差 `|模具重量 − 核对重量| / 模具重量` **> 10%** → 整单失败，逐条列出零件号、工序、Excel 行、两列重量与相对差；**不落库、不删已有布点**。缺外形的共用行跳过。模具重量为 0 而核对重量 > 0 同样拒绝。

覆盖键：**同一 `location` + `vehicle_model` 整表替换**（先删该基地该项目下全部模具主从表，再写入）。与工艺「还要带工厂和版本」不同。

### 5.2 列表、导出、删除：必须先选基地和项目

列表、导出、按作用域删除、上传都须先选 **基地 + 项目**。列表与导出 **不再筛供应商、版本**。禁止未选项目就拉全库。删除仍按基地+项目整包。

| | 规则 |
|--|------|
| 必选 | **采购基地** + **项目**（`vehicle_model`）。缺一不可。 |
| 不要 | 上传表单不选版本、不选冲压工厂。删除不按供应商/版本缩小。 |
| 列表 | **未选齐基地+项目不发列表请求、不出表数据**。可附加筛供应商、版本、零件号。 |
| 导出 | 前端未选齐基地+项目不得请求。内容含供应商、版本列；可按当前附加筛收窄。 |
| 删除 | **只做按作用域整包删**。参数基地 + 项目，缺一 → 400。删该组合下全部主从表。二次确认写明基地、项目。**禁止** `DELETE /{id}`。 |

### 5.3 依赖方向与路由挂载

- 属 **stamping 切片**（上游）。Router：`app/routers/stamping/die.py`（需要的话再拆 upload）。
- HTTP 前缀：**`/api/stamping/die`**。
- 上传 Service **只读**本切片工艺零件/工序 Repository 校验基地/项目及模具编号。禁止依赖 `costing`。
- 年度模具费计算 / 核价引擎只读本表（本切片不算金额）。

---

## 6. 分摊比例（仅子表）

**写死：**

| 字段 | 表 | 禁止 |
|------|-----|------|
| `alloc_ratio` 分摊比例 | **只在子表** `stamping_die_processes` | 主表不得汇总一列「总比例」（左右件 0.50 分属两件，单件求和无意义）；**主表不得有 `alloc_status`** |

`alloc_ratio` 回答的是共模拆账，不是寿命。

### 6.1 子表 `alloc_ratio`（分摊比例）

Excel **没有**比例列。新增工序由 Service 赋默认值；已存在的「零件号 + 工序号」覆盖上传时 **沿用库中值**（照抄 `ProcessCostRatioPreserver`）。

与加工费 `cost_ratio` 的唯一差别：**不要乘级进模 0.80**。下表只对照零件级叠乘；多序 PRG 例外只作用于加工费，见 [stamping-process-confirmation-design.md](stamping-process-confirmation-design.md) §4。

| 条件（模具方式或生产方式含关键字） | 加工费 `cost_ratio`（现网） | 模具 `alloc_ratio`（本模块） |
|-----------------------------------|------------------------------|------------------------------|
| 无共模、非级进 | 1.00 | **1.00** |
| 双槽 / 合并 / 一出二 | ×0.50 | **×0.50** |
| 级进模 | ×0.80 | **×1.00（忽略）** |
| 级进模 + 双槽/合并/一出二 | 0.40 | **0.50** |

关键字集合与现网一致：`双槽`、`合并`、`一出二`（「左右合并」「左右双槽」会被「合并」「双槽」命中）。  
扫描字段：**`die_method` + `production_mode`**。不要用 `die_type`（钢板模/铸造模）。

理由：0.80 是「级进模一次冲压更便宜」的 **加工费** 折扣；模具是一副工装的投资，级进并不自动打八折。共模（左右件同一副）仍应对半，避免左右各记 100%。

量化：`Decimal`，`Numeric(5,2)`，默认 `1.00`，与 `cost_ratio` 同精度。列表允许人工改（权限 `update`）。

覆盖上传：同零件号 + 工序号 **沿用** 已改过的 `alloc_ratio`；新工序用关键字默认值。不要求子表比例之和 = 1（左右件各 0.50 分属两行）。

---

## 7. 数据模型（规划）

唯一键主表：`location` + `vehicle_model` + `part_number`（**仍不含供应商、版本**）。  
子表：`die_part_id` + `process_seq`（零件内工序号唯一）。

建议表名：`stamping_die_parts` / `stamping_die_processes`。  
审计：`AuditUserMixin`。溯源：`excel_filename` / `excel_sheet_name` / `excel_row` / `excel_part_col`，对齐工艺零件。

主表增量字段（相对工艺件）：`sheet_shape`、`material_consumption`、`material_utilization`（**0～1**）、`estimated_weight_subtotal_t`、`die_method`、`production_mode`、`needs_end_effector`（**原文**）、`part_grade`。主表 **有** 从工艺回填的 `stamping_supplier`、`version`（非覆盖键）。主表 **无** `sketch_url`、**无** `alloc_status`。  
子表增量：`die_length` / `die_width` / `die_height`、`hollow_factor`、`estimated_weight_t`、**`alloc_ratio`（仅此表）**。  
物理量 / 比例一律 `Decimal`，禁止 `float`。

---

## 8. 分层与接口形态

Router 前缀 **`/api/stamping/die`**（stamping 切片下的 die）。示例：

```
GET    /api/stamping/die/template          下载导入模板
POST   /api/stamping/die/upload            start_upload（form：location、vehicle_model、file）
GET    /api/stamping/die/tasks/{task_id}   进度
GET    /api/stamping/die/parts             列表；query 必填 location + vehicle_model；page + size
GET    /api/stamping/die/parts/{id}        详情（主表 + 子表）
PATCH  /api/stamping/die/processes/{id}    子表 alloc_ratio
GET    /api/stamping/die/export            query 必填 location + vehicle_model
POST   /api/stamping/die/batch-delete      body 必填 location + vehicle_model；整包删
```

**禁止** `DELETE /api/stamping/die/parts/{id}`。

Parser：`app/parsers/stamping/die/`，可复用读格与合并单元格，**不要抽图**，不要塞进 `StampingExcelParser` 的列映射。

金额尚未出现；`material_utilization` JSON 用固定小数位字符串（0～1），不要 `float`。

---

## 9. 前端

冲压工程下新增二级分组 **「冲压模具」**（与「冲压工艺 / 冲次单价 / 冲压加工费」并列）：

| Hash | 标题 | 说明 |
|------|------|------|
| `#/stamping-die-upload` | 上传模具布点 | 基地 → 项目 → 拖拽；**下载模板**；进度对齐工艺上传 |
| `#/stamping-die-list` | 模具清单 | 先选基地+项目才出数；可筛供应商/版本；HUD 密表；操作列进详情；禁止整行点击；导出可按当前筛收窄；整包删除仍按基地+项目 |
| `#/stamping-die-unit-price` | 模具单价 | 档案 CRUD；基地+项目一条政策；操作列增改删 |

列表：未选基地或项目时展示空态（先选范围），**不要**用空参数打列表接口。选齐后再请求。顶栏：基地、项目，以及供应商、版本、零件号附加筛。**不要**筛分摊状态，HUD **不要**待分摊/不用分摊计数。  
详情：关注模具本身（类型/方式/尺寸/掏空/重量/套数/吨位/比例）。零件号仅作定位。不展示简图、材质利用率等工艺料信息。无单件删除。无主表分摊状态。

---

## 10. 权限（落地时按 permission-design §0）

建议树（实现时写入 `catalog.json` 并生成 `Perm.*`）：

```text
menu:stamping
  └── menu:stamping-die
        ├── menu:stamping-die-upload
        │     ├── op:stamping-die-upload:view
        │     └── op:stamping-die-upload:upload
        └── menu:stamping-die-list
              ├── op:stamping-die-list:view
              ├── op:stamping-die-list:update   # 子表比例
              ├── op:stamping-die-list:delete
              └── op:stamping-die-list:export
```

模具单价权限树见 [permission-design.md](../permission-design.md) 与 [stamping-die-unit-price-design.md](stamping-die-unit-price-design.md)，不要在本文件再抄一份。

---

## 11. 模具费用怎么用本表（本切片只落依据，不算金额）

本模块 **不是** 模具费结果表，而是计算的 **唯一上游布点依据**（对标：`stamping_processes` 之于冲压加工费）。本切片 **不读** 费用样例 Excel 的 AD+「模具款」列、**不定义** 单价公式。

金额路径已落地，一律读本表，不要再解析布点 Excel，也不要用工艺确认表吨位冒充模具费：

| 入口 | 行为 | 文档 |
|---|---|---|
| 冲压模具费计算页 | 手算年度 `final_die_fee` | [stamping-die-fee-design.md](stamping-die-fee-design.md) |
| 自动核价引擎 | 有布点且当年无结果 → `annual_die_fee` | [costing-engine-design.md](../costing/costing-engine-design.md) §5.2 / §13 |
| 冲压零件价页 | 只 lookup；缺档记 0 | 同上双轨 |

```text
各工序 estimated_weight_t ×（模具单价档案 / 分摊万台）× alloc_ratio
  → 汇总到零件最终模具费（元/件）
  → 零件价直接成本含该项；成品 I7/I8 间接费另议，不 silently 写入 gauge_alloc_fee
  → 满寿 / 多项目共用是否还摊：费用切片判定，不读本表 lifecycle 字段
```

与 I7 检具 / I8 器具：**不是同一笔**。I7/I8 仍按 L0 预留；本表是 **冲压件模具**。检具费维护走 `stamping_gauge_fees`。

---

## 12. 验收口径（实施后）

- 上传 / 列表 / 导出 / 整包删除：未传基地或未传项目 → 400。
- 列表未选齐时前端不请求；不得出现无作用域的全表查询。
- **没有** `DELETE …/parts/{id}`。
- 模型 / VO / 列表筛选 **不得出现 `version`**。
- `material_utilization` 入库为 0～1；Excel `65%` / `0.65` 都应落到约 `0.65`。
- `needs_end_effector` 存原文，不是 true/false。
- 所选项目不必已在工艺库；无工艺也可传布点。
- 文件车型与所选项目不一致 → 400。
- T13J 样本：88 主表、355 工序；同一零件工序号重复则整单失败。`Y=双槽` 且非级进 → `alloc_ratio=0.50`；`Z=级进模` 且 `Y=合并` → **0.50 不是 0.40**；纯级进无共模 → **1.00 不是 0.80**。
- 工序列、尺寸、吨位按单元格如实入库：格子写「合并」就记「合并」，空着就空着，不从上一件同工序补全。
- 子表 `die_number`：Excel 原文保留；有外形且空号由 Service 按 `DP-40-{项目}-流水` 补号。无尺寸的共用/合并行允许没有编号。
- 有完整长宽高+掏空且有预估重量时：与 7.85 外形核对重量相对差 > 10% → 整单失败，不改已有布点。缺外形行不查此项。
- AD～AJ 无任何字段入库；列 D 简图不入库；表头 V0-01 不落库。
- 再传同一基地+项目：人工改过的比例保留。
- 库表 / API：**不得出现** `alloc_status`；子表 VO 仅有 `alloc_ratio`。
- 路由均在 `/api/stamping/die` 下。无 `PATCH /parts/{id}`。

---

## 13. 修订

| 日期 | 说明 |
|------|------|
| 2026-09-19 | 纠正「计算是下一期 / 不进零件核价」：本切片仍只入库几何；金额已在模具费切片与引擎落地，读本表 |
| 2026-09-19 | 模具费 `source_die_part_id` RESTRICT：有模具费则不能删布点；工序 id 不加 FK |
| 2026-09-03 | APQP 落地：先布点后工艺；编号补号；布点不认供应商 |
| 2026-09-02 | 交叉引用家模副产品：布点空板料不覆盖工艺表 |
| 2026-08-28 | 初稿：A–AC 导入、基地+项目来自冲压、主表分摊状态、子表分摊比例（共模 0.50、不用级进 0.80） |
| 2026-08-28 | 写死：`alloc_status` 仅主表；子表只有 `alloc_ratio`，工序行不确认状态 |
| 2026-08-28 | 背景：模具按 10 万件寿命摊；多项目共用已满寿则主表标「不用分摊」，与其它未满寿零件脱钩 |
| 2026-08-28 | 不管理简图：列 D 跳过，无 `sketch_url`、不抽嵌入图 |
| 2026-08-28 | 定位：本模块是计算模具费用的依据；本期落库不算额，算费必须读本表 |
| 2026-08-28 | 落地：表、上传/列表/导出/整包删除、权限与前端 |
| 2026-08-28 | 去掉主表 `alloc_status` 与列表统计：本期只关心模具本身，寿命/是否还摊留给计算层 |
| 2026-08-28 | Parser：按表头映射列；纵向合并不串列；工序列的「共用/合并」视为共模标记，尺寸沿用上一件同工序 |
| 2026-08-29 | Parser：取消同工序尺寸/代号补全，Excel 有则有、无则无 |
| 2026-08-29 | 子表 `die_number`：从冲压工序按零件号+工序号取唯一非空编号（随后改为缺/冲突整单失败，见下） |
| 2026-08-29 | 布点上传：须先有工艺确认表；找不到零件/工序、有尺寸无唯一模具编号 → 整单失败并列出原因 |
| 2026-08-29 | 核对失败文案带工艺确认表 Excel 文件名与冲压厂 |
| 2026-08-29 | 模具编号冲突按全厂+全版本比对；失败清单含版本且任务说明不再截断 |
| 2026-08-29 | 布点同一零件工序号重复则整单失败，不再默默去重 |
| 2026-08-29 | 布点 Parser 与工艺 HeaderResolver 各用各的标题短语，不再交叉识别 |
| 2026-08-29 | 单价档案另表，见 stamping-die-unit-price-design.md |
| 2026-08-29 | 检具费档案另表，见 stamping-gauge-fee-design.md；布点仍不读 AD+ 检具款 |
| 2026-08-30 | 布点导入：有完整外形时模具重量与核对重量相对差 > 10% 整单拒绝 |
| 2026-08-30 | 布点从冲压工艺回填供应商与版本；对不上或一对多则整单拒绝 |
| 2026-08-30 | 模具清单列表/导出可筛供应商与版本；导出含这两列 |
