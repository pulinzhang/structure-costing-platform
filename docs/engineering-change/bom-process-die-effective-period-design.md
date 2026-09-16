# BOM / 冲压工艺 / 模具有效期 — 现网改造

> 状态：**设计稿（未落地）**  
> 用途：改造现网三套主数据，使一个项目在生命周期里换总成、换工艺件、换布点件时，**新旧行都留在库里，按月命中**。  
> 本文只谈这三块。不是工程变更合册，也不是一口价年内分段。  
> 关联：[材料清单 / 采购对象](../bom/bom-procurement-objects-design.md)、[冲压工艺确认表](../stamping/stamping-process-confirmation-design.md)、[模具布点](../stamping/stamping-die-management-design.md)、[项目](../masterdata/vehicle-model-design.md)、[总成月核价](../costing/assembly-costing-design.md)、[月度引擎](../costing/costing-engine-design.md)。  
> 合册切点入口（以后）：[工程变更](part-number-revision-design.md)。  
> 协议价分段（另一件事）：[年度协议价生效期](../costing/effective-period-design.md)。

---

## 0. 一句话

> **有效期写在 BOM 树根、冲压零件行、模具零件行上。查看与核价带年+月。现网整包覆盖导入改成按对象对齐，禁止把没出现在文件里的行删掉。**

项目会变。现网按「一份当前包永远正确」建模，核价月只决定钢价，不决定用哪棵树、哪条工艺。本改造补这一层。

已否决：生失效写在 `bom_snapshots` / 工艺包头版本 / 布点「基地+项目」整包上；用 `status`、日历日、新 `bom_version` 当切点；同号只保留最新一行。

---

## 1. 三块共用

字段名对齐 `vehicle_models`：

| 列 | 规则 |
|----|------|
| `effective_year` / `effective_month` | 必填；月 1–12 |
| `expiry_year` / `expiry_month` | 同空或同有；有则不得早于生效；空 = 仍有效 |

命中（跨年，闭区间）：

```text
effective <= as_of_month 且（expiry 空 或 as_of_month <= expiry）
```

`as_of_month` = 查询或核价的年+月。未选月：墙钟月（或该基地最近核价月，产品定一处，BOM / 工艺 / 布点 / 总成核价一致）。

重叠：同一业务键同一月不得两行都命中。相邻合法（7 月失效、8 月新生效）。空洞合法（该月无命中 = 该对象该月不存在，不拿邻月顶上）。SQLite 无 exclusion，写入前 Service 校验；弱 UNIQUE 只防完全重复。

纯函数放 `app/common/`（从项目 `identity.py` 抽出或并列）。**不是** 协议价那种「年内 from–to」。各切片 Repository 提供 `as_of_month(...)`；costing 只调上游，禁止在 rollup 里自己比年月。

列表默认只出命中行。开关 `include_expired`（含已失效）默认关；失效行必须标出生失效。

导入表单 **不要** 用墙钟月或手填月去盖第一次 SOP。已有行改生失效走 **单条 update**（§1.2）；后续再插入的新号才用表单切点月（见各块写入）。导入更新已有行时 **不得** 改这四列。

### 1.1 第一次导入 = 项目 SOP

该块在该项目下还没有任何行 → 整表插入视为 **项目第一次 SOP**：

- 材料清单：该基地+项目尚无 snapshot / 无 L0  
- 工艺：该基地+项目+冲压厂尚无 `stamping_parts`（该厂第一份确认表）  
- 布点：该基地+项目尚无 `stamping_die_parts`  

生失效仍抄 **项目** 起止，不抄墙钟、不另开工厂自己的月。

每一行（BOM 只写 L0）的生失效 **整份抄项目主数据**，不另开口径：

| 行上 | 来自 `vehicle_models` |
|------|----------------------|
| `effective_year` / `effective_month` | 项目开始年/月（必有） |
| `expiry_year` / `expiry_month` | 项目结束年/月；**项目里空则行上也空** |

上传页可只读展示「本文件按项目 SOP 时段：xxxx年x月 – （空=未结束）」，禁止第一次 SOP 改成别的月。项目未登记或没有开始月 → 硬停，去项目档案补，不要默认为当天。

存量迁移与第一次 SOP 同一规则：已有行补列时也抄项目起止，项目结束空则失效空。

### 1.2 单条编辑必须能改生效、失效

现网三块都有「点开一条再保存」。改造后这条 update **必须带生效、失效**，不能只在导入或只改失效。

界面文案可以写「生效日期」「失效日期」，粒度仍是 **年+月**（与项目主数据同一套控件），禁止日历日。失效两格同空 = 未结束。

| 对象 | 现网单条入口 | 改造 |
|------|----------------|------|
| BOM L0 | 结构/扁平目前几乎不能改节点时段（无节点 PATCH） | 新增 `PATCH /api/bom/nodes/{id}`：body 含 `effective_year/month`、`expiry_year/month`。仅 `level=0`；L1/L2 调此接口 → 拒绝。详情/树节点编辑页可改这两项并保存 |
| 冲压零件 | 详情已有 `PATCH …/parts/{id}/offal`、`PUT …/parts/{id}/processes` | 新增 `PATCH /api/stamping/parts/{id}/period`（或详情一次保存并入现有 update，权限仍 `op:stamping-parts:update`）。GET 详情 VO 必须带回四列 |
| 模具零件 | 详情只 `PATCH` 工序分摊比例 | 新增 `PATCH /api/stamping/die/parts/{id}/period`（权限仍布点 `update`）。GET 详情 VO 带回四列 |

写入规则（三块同一套 Service 校验，不要各写 if）：

1. 生效年、月必填，月 1–12。  
2. 失效年、月同空或同有；有则不得早于生效。  
3. 与同业务键 **其它行** 时段不得重叠（改自己这一行时排除本 `id`）。  
4. 有加工费 / 模具费引用 **不挡改期**（行还在，只换命中月）。  
5. 保存后列表、核价 as_of 立刻按新时段走；已审核月账仍不自动重算。

不要：只能改失效不能改生效；只能列表快捷改、详情保存丢字段；Excel 再导把单条改过的时段覆盖回去。

---

## 2. BOM（材料清单）

### 2.1 现网

| 项 | 现网 |
|----|------|
| 头表 | `bom_snapshots` UNIQUE `(location, vehicle_model, bom_version)` |
| 树 | `bom_nodes` 挂 `snapshot_id`；L0=`parent_id` 空 |
| 导入 | 同键且无采购对象/焊接拆解 → **删整棵森林再写** |
| 列表 | `BomSnapshotQuery` 无核价月；结构/扁平看整份 snapshot |
| 核价 | `list_by_snapshot` 全量 L0；引擎每个 `bom_version` 都算 |

`bom_version`、头上 D/09、`status`（draft/active/archived）**都不是** 总成切点。D/09 只标 SOP 那一版清单字。芜湖 T13J 改造后仍是 **一份** snapshot，林子里同时有有效树和失效树。

### 2.2 改造

四列加在 **L0**（`level=0`）。L1/L2 禁止非空；子孙跟树根走。

弱 UNIQUE：`(snapshot_id, part_number, effective_year, effective_month)`，仅 L0。同一 snapshot、同一总成号，时段不得重叠。同一 `seq_no` 在同一月至多一棵有效树（列表按月过滤时）；「含已失效」时同一序号可多棵。

`bom_snapshots` 不加生失效。不要为一次铰链换号再新建 D/10 当有效期。

### 2.3 写入

`bom_upload_service`：禁止再「删 snapshot 下全部节点再插入」。

- 该项目尚无清单（第一次 SOP）→ 整表插入，每个 L0 生失效抄项目起止（结束空则空）。  
- 文件中的 L0 零件号库里没有 → 插入整棵，根上写 **表单切点月**（已有森林之后的新树，不是 SOP）。  
- 库里已有同号 L0 → 更新该树属性/子孙（仍按现网 Parser），**生失效不动**。  
- 文件没有、库里有的 L0 → **留下**。生失效由 §1.2 单条 PATCH 改。  
- 真删除 snapshot（管理删除）仍走现网下游引用保护。

不要用 snapshot `status=archived` 代替树根失效。

### 2.4 读

结构树、扁平、采购对象一览、焊接拆解展示：带 `year`+`month`，只展开该月命中的 L0 及其子孙。`include_expired` 例外。

`BomNodeRepository.list_by_snapshot(db, snapshot_id, as_of=...)`：不过滤子孙行，过滤时先收集命中的 L0 id 再收子树。

采购对象、焊接费仍可按 snapshot 生成（历史对象留着）；**算当月、列当月** 只认树根命中的那些 `source_node_id`。

### 2.5 核价

`assembly_cost` `prep` / `ready`：仍 `get_by_unique_key(location, vehicle_model, bom_version)`，然后丢掉未命中 L0。失效树根不出本月卡。

引擎：每个可引入项目 **一个** 结构范围 = SOP 那份 snapshot + 该月有效森林。废止「该项目每个 `bom_version` 都进 L0Scope」。

---

## 3. 冲压工艺确认

### 3.1 现网

| 项 | 现网 |
|----|------|
| 表 | `stamping_parts` + `stamping_processes`（拼焊子片另表） |
| UNIQUE | `(location, stamping_supplier, vehicle_model, version, part_number)` |
| 导入 | 同范围 `delete_by_scope` 再写；有加工费则拒绝覆盖 |
| 列表 | `StampingPartQuery`：**无年、无月**；靠项目+版本筛 |
| 零件价 / 加工费 | 该项目（该版本）下全部零件；`dict[part_number]` 会后写覆盖 |

`version` 来自确认表头/文件名，是 SOP 字，不是切点。上传页不选手选基地项目（从表头解析 + 项目可引入带出基地）。

### 3.2 改造

四列加在 `stamping_parts`。工序、拼焊子片跟零件行走，不加列。

**身份不再含 `version`。** 弱 UNIQUE：`(location, stamping_supplier, vehicle_model, part_number, effective_year, effective_month)`。`version` 列保留展示/溯源。同一号改工艺但不换号：截断旧行失效月、插新行，不要靠改 version 冒充两段。

有加工费：现网「整包不能覆盖」。改造后不整包删，改为：已有加工费的零件行 **禁止删除**；允许新增其它号；改失效月不删行、不级联删 `stamping_process_fees`。算某月加工费/零件价只绑该月命中的 `stamping_parts.id`。

### 3.3 写入

`upload/persist.py`：**去掉** `delete_by_scope` 作为日常导入。

按 `(location, stamping_supplier, vehicle_model, part_number)` 找 **当前未失效** 行（或唯一现行）：

- 该冲压厂在该项目下尚无工艺行（第一次 SOP）→ 整表插入，每件生失效抄项目起止（结束空则空）。  
- 没有现行 → 插入，生效=表单切点月（已有工艺之后的新号）。工艺上传现无切点控件：第一次 SOP 不需要；非 SOP 新增与 BOM/布点同一「切点年月」。  
- 有 → 更新材料/工序/子片（沿用现网利废、家模、比例保留规则），**生失效不动**。  
- Excel 没有的号 → **不删**。

列表 PATCH 见 §1.2。批量删除范围键不要再靠 version 当「整包」；按 id 或按号+时段删，有加工费 RESTRICT 照旧。

### 3.4 读

`StampingPartQuery` 增加 `year`、`month`、`include_expired`。默认 as_of 过滤。版本下拉不再当「这个月用哪包工艺」。

零件价、加工费、钢材测算、导出：只取该月命中行。树上叶子抄 `unit_cost` 时按零件号命中 **该月那一行**，禁止 `dict[part_number]` 多行后写。

引擎 PartCost：该月可引入项目下，只计划命中的工艺行（不是该车全部历史号）。

---

## 4. 模具布点

### 4.1 现网

| 项 | 现网 |
|----|------|
| 表 | `stamping_die_parts` + `stamping_die_processes` |
| UNIQUE | `(location, vehicle_model, part_number)` — **同号只能一行** |
| 导入 | `delete_scope(location, vehicle_model)` 整项目替换 |
| 列表 | `StampingDiePartQuery` 无年+月（筛选级联上的年+月只用于项目可引入） |
| 回填 | 供应商、版本从同项目工艺回填，不是覆盖键 |
| 模具费 | 读该项目全部布点行 |

### 4.2 改造

四列加在 `stamping_die_parts`。工序跟零件走。

弱 UNIQUE 改为含生效年月，允许同号前后两段。同号时段不得重叠。

`version` / `stamping_supplier` 仍可从工艺回填，**不**当有效期。

有模具费行引用：与工艺相同，禁止删被引用的布点行；改期走 §1.2，不删行。算某月模具费只取命中行。

检具费本改造 **不强制**（可同期加四列，引擎不挡）；不要用布点有效期冒充检具。

### 4.3 写入

`die/upload_service.py`：**去掉** 整项目 `delete_scope`。

第一次 SOP（该基地+项目尚无布点行）：整表插入，每件生失效抄项目起止（结束空则空）。其后按 `(location, vehicle_model, part_number)` 对齐现行：有则更新尺寸/工序（`alloc_ratio` 仍按零件号+工序号沿用已改值）；无则插入并写表单切点月。Excel 没有的号不删。补号 `DP-40-{项目}-流水` 扫描 **含已失效行已占用的号**，避免复号。

表单已有基地 + 可引入项目。第一次 SOP 不选手填生效月；非 SOP 新增才出切点年月。单条改期见 §1.2。

### 4.4 读

`StampingDiePartQuery` 增加 `year`、`month`、`include_expired`。列表/导出默认 as_of。

模具费计算、间接费摊模具：该月命中行。无命中 = 该件该月无布点，不用失效行顶上。

---

## 5. 下游（现网必须一起改，否则三张表改了核价仍全量）

| 调用方 | 现网 | 改造 |
|--------|------|------|
| 总成 `prep` / `ready` / 还原树 | 整份 snapshot | 该月有效 L0 森林 |
| 采购对象覆盖检查 | 清单上头整包 | 只要求该月有效树有对象 |
| 焊接费覆盖 | 当前树全节点 | 只覆盖有效树节点 |
| 冲压零件价 / 加工费 | 范围下全部 `stamping_parts` | `as_of` |
| 模具费 | 项目下全部布点 | `as_of` |
| 引擎发现 L0Scope | 每项目每个 `bom_version` | 每项目一份 SOP 快照 + 有效森林 |
| LLM 就绪「清单不按年失效」 | 有 snapshot 即绿灯 | 该月至少一棵有效 L0 |

已审核月账不覆盖。反审重算按 **当时主表 as_of**，所以 AA 必须留在库里。

---

## 6. 迁移

三张主表存量：与第一次 SOP 相同，抄该行所属 `vehicle_models` 的开始月与结束月；项目结束空则失效空。

上线前扫描：

1. 同一 snapshot 两个 L0 同零件号。  
2. `stamping_parts` 去掉 version 身份后，同厂同项目同号多行（不同 version）。  
3. 布点同项目同号本就 UNIQUE，一般无重复。  

有冲突：人工截断时段或合并，禁止静默删行。两份 `bom_version` 头并存：不自动合并；核价按月只收有效 L0。若两份头同号 L0 会在同月双命中 → 先处理再开 as_of。

---

## 7. 界面（三页同一习惯）

材料清单结构/扁平、冲压工艺列表、模具布点列表：筛年、月；默认过滤命中。

**列表必须有两列：生效日期、失效日期。** 不要只放详情里。绑定 `effective_year/month`、`expiry_year/month`，展示 `YYYY-MM`（例 `2026-08`）。失效空显示「未结束」，不要空白得像没做。不要日历日、不要只显示年。

| 列表 | 谁出这两列 |
|------|------------|
| 材料清单结构 / 扁平 | **仅 L0 行**；L1/L2 这两格空（跟树根走，不重复写） |
| 冲压工艺零件列表 | 每一零件行 |
| 模具布点零件列表 | 每一零件行 |

列表 VO 必须带四列，前端不要自己猜。列放在零件号/名称附近，三页同一顺序：先生效、后失效。

**单条编辑**（详情抽屉 / 树节点）：生效日期、失效日期都可改、都要能保存，走 §1.2 update。权限与现网该对象 `update` 同一级。L1/L2 不出现这两项。

不要用「BOM 版本」「工艺版本」下拉代替月份。

上传页：第一次 SOP 只读展示项目起止，不选手填月。已有数据后再导新号，才出现切点年月；说明「只给文件里的新行；旧行不会因为本次没出现而被删除」。

---

## 8. 本文不做

| 不做 | 说明 |
|------|------|
| 工程变更菜单、合册 Excel、变更头自动种树 | [part-number-revision-design.md](part-number-revision-design.md) |
| AB 继承 SOP 序号、设变自动带采购对象 | 同上 |
| 一口价/焊接单价年内分段 | [effective-period-design.md](../costing/effective-period-design.md) |
| 取价 AB 回退 AA；库内复制出新号 | 否决 |

改造完成后：先导入新号（不删旧号），再在列表把旧行失效到切点前一月。账即按月分开。合册只是以后少点这几下。

---

## 9. 验收

1. 项目尚无清单/工艺/布点时第一次导入：行上生效=项目开始月，失效=项目结束月；项目结束空则行上失效空。不得写成墙钟月。  
2. 零件/树根/布点详情打开，改生效或失效（含清空失效）能保存；同号重叠被拒绝。再导 Excel 不会把这次改期盖掉。  
3. 同一 T13J D/09 快照里 3086AA 失效到 7 月、3086AB 从 8 月起。7 月结构与总成核价只有 AA，8 月只有 AB。  
4. 再导一份只含部分总成的材料清单，其它 L0 还在。  
5. 再导工艺确认（部分件或新号），3096AA 还在。  
6. 再导布点（部分件），未出现的布点行还在。  
7. 三页列表都能看见生效日期、失效日期两列；L0/零件行有值，BOM 子孙这两格空；失效空为「未结束」。  
8. 反审 7 月重算，树仍是 AA。  
9. 引擎 8 月不会把已失效树和第二个 `bom_version` 再算一套。

---

## 10. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-16 | 现网改造专稿：BOM 树根、冲压零件、模具零件三块并列；停整包覆盖；下游 as_of。 |
| 2026-09-16 | 第一次导入=项目 SOP：生失效抄项目起止；项目结束空则行上失效空。 |
| 2026-09-16 | 单条编辑 update 必须能改生效、失效；导入不覆盖已改时段。 |
| 2026-09-16 | 前端列表固定列：生效日期、失效日期。 |
