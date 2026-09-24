# BOM / 冲压工艺 / 模具有效期 — 现网改造

> 状态：**现网改造进行中**  
> **本期范围：** BOM / 冲压工艺 / 模具布点三块自身（表、导入按对象对齐、单条改期、本切片列表/树按月命中），以及 **冲压加工费 / 冲压模具费按零件（布点）年交集取件**、**冲压零件价格计算按零件月命中取件**、**总成核价按节点月命中取件**、**核价引擎发现按零件/L0 as_of 再滤项目月**。  
> **拆解与焊接费（计算已落地）：** 拆解表不落生失效，取期 join `source_node_id` 再认 **L0 树根**。`#/bom-welding-fee-calc` 入参 **年 + 基地 + 项目**，跟拆解列表，按树根年交集取树；**不靠版本号、不靠 snapshot**。见 §6。  
> **本期仍不动：** LLM、零件用在哪。下游其它入口仍可能按现网读全量。  
> **采购对象（列表 / 设变插行已落地）：** 对象行不落四列；列表默认包含已过期、join 树根；整包 generate 门禁见 [采购对象 §14](../../bom/bom-procurement-objects-design.md)。  
> 本文不是工程变更，也不是一口价年内分段。  
> 关联：[材料清单 / 采购对象](../../bom/bom-procurement-objects-design.md)、[冲压工艺确认表](../../stamping/stamping-process-confirmation-design.md)、[模具布点](../../stamping/stamping-die-management-design.md)、[焊接工艺拆解](../../bom/welding-process-breakdown-design.md)、[焊接费](../../bom/welding-fee-design.md)、[项目](../../masterdata/vehicle-model-design.md)、[核价引擎](../../costing/costing-engine-design.md)。  
> 工程变更切点入口（以后；**设计让步给现网**，落地只改三条写入门禁）：[工程变更](part-number-revision-design.md)。  
> 协议价年内分段已否决，见 [年度协议价生效期](../../costing/effective-period-design.md)。本文的生失效继续按现网。  
> 下游 as_of：总成月核价与引擎 `start_run` 已接零件/节点月命中；计算身份另按账期问项目期。采购对象列表是档案（默认包含已过期、join 树根），见 [采购对象 §14](../../bom/bom-procurement-objects-design.md)；核价侧仍按账期月裁树。

---

## 0. 一句话

> **有效期写在 BOM 每个树节点、冲压零件行、模具零件行上。本切片查看带年+月。现网整包覆盖导入改成按对象对齐，禁止把没出现在文件里的行删掉。**

项目会变。现网按「一份当前包永远正确」建模。本改造只在这三套主数据上补「按月命中」；先让库里能同时留新旧行、列表能按月看见，再谈核价。焊接工艺拆解是派生结果表：范围三列现网已落；**生失效永远读 source `bom_nodes`，不在拆解行再抄一份**。不是第四套 SOP 导入。

已否决：生失效写在 `bom_snapshots` / 工艺包头版本 / 布点「基地+项目」整包上；用 `status`、日历日、新 `bom_version` 当切点；同号只保留最新一行。

---

## 1. 页面与 API

级联上的年+月 **只筛项目是否可引入**，不是树/零件 as_of。上传门禁用墙钟月问 `require_introducible`。展示年月用现网 `fmtPeriod`（`2026年07月`），不要 `2026-08`。

### 1.1 BOM

| 页 | Hash | 读 | 写 |
|----|------|----|----|
| 上传材料清单 | `#/bom-upload` | `GET /api/bom/filters/cascade`（墙钟年+月 → 可引入项目） | `POST /api/bom/upload` Form：`location` + `vehicle_model` + file → `task_id`；`GET /api/bom/upload/tasks/{task_id}` 轮询 |
| 材料清单列表 | `#/bom-material` | `GET /api/bom/snapshots`（`BomSnapshotQuery`：基地/项目/版本/状态，**无年+月**） | `DELETE /api/bom/snapshots/{id}`（有采购对象/焊接拆解则 409） |
| 产品结构 | `#/bom-structure` | 先 `GET /snapshots` 出项目卡；进清单后 `GET /snapshots/{id}` + `GET /snapshots/{id}/tree`，前端把 `level===0` 当总成卡 | 无节点编辑 |
| 产品结构图 | `#/bom-viz` | 同上 `GET …/tree` | 无 |

写入走 `BomUploadService.start_upload`（`task_id` 轮询）→ 指挥家；落库见 §3.2：**按树对齐，不删 snapshot**。`POST /snapshots`、`POST /snapshots/{id}/nodes` 路由在，前端不用。节点有 `DELETE /api/bom/nodes/{id}` 与生失效 PATCH。扁平 `GET …/nodes` 前端不用，结构/结构图都吃 `/tree`。

`bom_snapshots` UNIQUE `(location, vehicle_model, bom_version)`。节点带基地/项目/版本与四列生失效，见 §3.1。头上 D/09、`status` **不是** 总成切点。同一份 snapshot 里可同时有有效树和失效树。

### 1.2 冲压工艺

| 页 | Hash | 读 | 写 |
|----|------|----|----|
| 上传工艺文件 | `#/stamping-upload` | 无范围控件 | `POST /api/stamping/upload/` **只传 file**（异步）。项目/厂从表头解析，基地由可引入项目带出 |
| 冲压零件列表 | `#/stamping-parts` | `GET /api/stamping/parts/list`（`StampingPartQuery`：基地/项目/**版本**/厂/零件号，**无年+月**）；级联 `GET /api/stamping/filters/cascade` 的年+月只问可引入项目 | 详情：`PATCH …/parts/{id}/offal`、`PUT …/parts/{id}/processes`、`PATCH …/processes/{id}`。删：`DELETE …/parts/{id}`；`POST …/parts/batch-delete` 键仍是基地+项目+**版本**（厂可选） |

落库 `upload/persist/parts.py`：按号更新已有行，**不** `delete_by_scope`。文件里没有的号留下；已有 SOP 后文件出现新号 → 整单拒绝。覆盖前 `cost_ratio_preserver` 按零件号+工序号沿用已改比例。UNIQUE `(location, stamping_supplier, vehicle_model, part_number)`（无 `version`）。`version` 列仍在，是确认表 SOP 字，不是切点。细则 §4.2。

本切片导出（`/parts/export-download`）必须带 `year`、`month`。钢材测算导出无库内命中行则不出文件。**冲压加工费计算按冲压件有效期与计算年做年交集**，见 §4.4；不要再用项目 `require_overlaps_year` 当取件 WHERE。零件价列表 **本期不改**。

### 1.3 模具布点

| 页 | Hash | 读 | 写 |
|----|------|----|----|
| 上传模具布点 | `#/stamping-die-upload` | `GET /api/stamping/die/filters`（年+月 → 可引入项目） | `POST /api/stamping/die/upload` Form：`location` + `vehicle_model` + file（异步） |
| 模具清单 | `#/stamping-die-list` | `GET /api/stamping/die/parts`（`StampingDiePartQuery`：**必须**基地+项目，无年+月）；筛选项同年+月只问可引入 | 详情只 `PATCH /api/stamping/die/processes/{id}`（`alloc_ratio`）。`POST /batch-delete` 整项目；`GET /export` 无 as_of |

落库 `die/upload/service.py`：`delete_scope(location, vehicle_model)` 整项目替换，再 `preserve_die_alloc` 按零件号+工序号沿用分摊。UNIQUE `(location, vehicle_model, part_number)` — **同号只能一行**。`version` / `stamping_supplier` 可从工艺回填，不是覆盖键。**冲压模具费计算按布点零件有效期与计算年做年交集**，见 §5.4；不要再用项目 `require_overlaps_year` 当取件 WHERE。

---

## 2. 三块共用

字段名对齐 `vehicle_models`：

| 列 | 规则 |
|----|------|
| `effective_year` / `effective_month` | 必填；月 1–12 |
| `expiry_year` / `expiry_month` | 同空或同有；有则不得早于生效；空 = 仍有效 |

**生失效四列永远不得进入 UNIQUE。** 三块同一纪律。时段只做列、按月命中、单条 PATCH，不当身份。L0 / 工艺零件 / 布点零件：同一号只有一行；换号是新零件号、新行。L1 同号可挂在不同树上。

命中（跨年，闭区间）：

```text
effective <= as_of_month 且（expiry 空 或 as_of_month <= expiry）
```

本期 `as_of_month` **只服务这三块的列表/树/本切片导出**。列表/树未带月 = **墙钟月**（与项目一览、上传 `require_introducible` 同一套 `now()`）。不要绑「最近核价月」——核价本期不动，绑了会对不齐。

**凡从库里按命中倒出的导出，必须带 `year`、`month`。前端必须给出这个参数。** 含本切片工艺确认导出、布点导出，以及以后工程变更倒出当月树/工艺/布点。跟列表当前筛到的月同一套，不要另开「导出用墙钟」。接口缺年或月 → **422**，禁止后端默 `now()`、禁止默最近核价月。空模板（无库内命中行）下载不按月裁，不要求 as_of。文件名或表头带 `fmtPeriod`，打开即知是哪一月。

列表默认只出命中行。产品结构 / 结构图可开 `include_expired`（含已失效，默认关）。**冲压零件列表、模具清单不提供该开关**：已有查看年+月，只出该月命中行。失效行必须标出生失效。同一 `seq_no` 在同一月至多一棵有效树（按月过滤时）；结构图打开「含已失效」时同一序号可多棵——这是 Service 命中规则，**不是** UNIQUE。空洞合法（该月无命中 = 该对象该月不存在，不拿邻月顶上）。相邻月（7 月失效、8 月新生效）合法。

纯函数放 `app/common/`（从项目 `identity.py` 抽出或并列：`period` / `validate_period` / `is_in_period`）。**不是** 协议价那种「年内 from–to」。三块 Service 调同一套，不要各写 if。

下游继续走现网全量读法：`BomNodeRepository.list_by_snapshot` **保持无过滤**（签名不要改成必填 as_of）。本切片树/扁平在 **Service** 里按命中 L0 收子树。工艺 `paginate` / 布点 `paginate`：列表入口带 as_of；costing 现用的 `list_by_location_and_vehicle` / `list_parts_for_scope` **不要改默认行为**（加工费 / 模具费计算另传年交集，见 §4.4、§5.4）。

这三页上传 **只做 SOP**。投产后改图、新旧并存，必须走 [工程变更](part-number-revision-design.md)，不要在本页选手填切点月、不要把再导当成设变。导入更新已有行时 **不得** 改这四列。已有行改生失效走 **单条 update**（§2.2）。

### 2.1 第一次导入 = 项目 SOP

该块在该项目下还没有任何行 → 整表插入视为 **项目第一次 SOP**：

- 材料清单：该基地+项目尚无 snapshot / 无 L0
- 工艺：该基地+项目+冲压厂尚无 `stamping_parts`（该厂第一份确认表）
- 布点：该基地+项目尚无 `stamping_die_parts`

生失效仍抄 **项目** 起止，不抄墙钟、不另开工厂自己的月。

每一行的生失效 **整份抄项目主数据**，不另开口径（BOM 是树上 **每一个节点**，含 L1/L2，不是只写 L0）：

| 行上 | 来自 `vehicle_models` |
|------|----------------------|
| `effective_year` / `effective_month` | 项目开始年/月（必有） |
| `expiry_year` / `expiry_month` | 项目结束年/月；**项目里空则行上也空** |

上传页文案与控件见 §8.1。禁止第一次 SOP 改成别的月。项目未登记或没有开始月 → 硬停，去项目档案补，不要默认为当天。

存量迁移与第一次 SOP 同一规则：已有行补列时也抄项目起止，项目结束空则失效空。

### 2.2 单条编辑必须能改生效、失效

现网三块都有「点开一条」。改造后这条 update **必须能改生效、失效**，不能只在导入或只改失效。

界面文案可以写「生效日期」「失效日期」，粒度仍是 **年+月**（与项目主数据同一套控件），禁止日历日。失效两格同空 = 未结束。

| 对象 | 现网单条入口 | 本期 |
|------|----------------|------|
| BOM 节点 | 结构/结构图不能改节点；无 PATCH | 新增 `PATCH /api/bom/nodes/{id}`：body 含四列。仅 `level=0`；保存后 **级联写该棵子树所有节点** 同一套生失效。L1/L2 调此接口 → 拒绝（节点上有四列，但不独立改期）。结构页总成卡 / 结构图 L0 可改并保存 |
| 冲压零件 | `PATCH …/offal`、`PUT …/processes` | 新增 `PATCH /api/stamping/parts/{id}/period`（权限仍 `op:stamping-parts:update`）。GET 详情 VO 带回四列 |
| 模具零件 | 只 `PATCH` 分摊比例 | 新增 `PATCH /api/stamping/die/parts/{id}/period`（权限仍布点 `update`）。GET 详情 VO 带回四列 |

写入规则（三块同一套校验）：

1. 生效年、月必填，月 1–12。
2. 失效年、月同空或同有；有则不得早于生效。
3. 同一 snapshot 同一 `seq_no` 的 **其它 L0** 不得与本行在同一月都命中（改自己时排除本 `id`）。工艺/布点一行一号，没有「同号其它行」可重叠。
4. 有加工费 / 模具费引用 **不挡改期**（行还在，只换命中月）。改期后，加工费 / 模具费 **下一次按年计算** 只收该年与零件（布点）期有交集的行，已算出的旧年结果行不自动删。
5. 保存后 **本切片列表/树** 立刻按新时段走。零件核价月账本期不读这四列，故不会自动变。

不要：只能改失效不能改生效；只能列表快捷改、详情保存丢字段；Excel 再导把单条改过的时段覆盖回去。

---

## 3. BOM

### 3.1 改造

`bom_nodes` **每一行**（L0 / L1 / L2）必须自带范围与时段，禁止只靠 join `bom_snapshots`、禁止 L1/L2 这几列为空：

| 列 | 规则 |
|----|------|
| `location` | 必填；与所属 snapshot 同一基地 |
| `vehicle_model` | 必填；与所属 snapshot 同一项目 |
| `bom_version` | 必填；与所属 snapshot 同一清单版本（界面称「版本」） |
| `effective_year` / `effective_month` | 必填；月 1–12 |
| `expiry_year` / `expiry_month` | 同空或同有；空 = 未结束 |

写入时 `location` / `vehicle_model` 必须与所属 snapshot 同一基地、同一项目。`bom_version`：**SOP 导入抄头**（如 D/09）；**禁止**做成「节点版本永远等于头」的硬约束——工程变更要在同一份 snapshot 里给新树写变更字，头上仍留 SOP 那一版。同一棵树（一个 L0 及其子孙）生失效 **同值**：SOP 插入时每个节点都抄项目起止；PATCH 树根后级联写子树。不要让子件自己另开一段有效期。

**级联版本下拉（`GET /api/bom/filters/cascade` 的 `bom_versions`）：** 只对 **L0** 节点 `bom_version` 去重。工程变更写入 `EC-202505` 后一览能看见该字。有年+月时只收该月命中的 L0。不要用 snapshot 头当版本下拉。

UNIQUE 只约束 L0：`(snapshot_id, part_number)`。**不含** 生失效。同一 snapshot、同一总成号只有一行（3086AA 与 3086AB 是两个号）。同一 `seq_no` 在同一月至多一棵有效树（列表按月过滤时）；「含已失效」时同一序号可多棵——Service 校验，不进 UNIQUE。

`seq_no` 是 SOP 槽位。第一次 SOP 从 Excel 写入后，本页再导已有树 **不得改** L0 `seq_no`（工程变更的 AB 要继承这个号）。`sort_no` / `excel_row` 可随文件更新。

`bom_snapshots` 不加生失效。不要为一次铰链换号再新建 D/10 当有效期。`#/bom-material` 仍是清单头列表，**不加** 生效/失效列（列在节点上，不在头上）。

节点 `(location, vehicle_model)` 复合外键对齐 `vehicle_models`（与头表同一套 RESTRICT）。头上的 `bom_version` 不另当切点。

### 3.2 写入

`upload/persist/nodes.py`：按树对齐，**不删 snapshot**。真删除 snapshot 仍走 `assert_bom_scope_unused`（有采购对象/焊接拆解则 409）。再导不挡「更新文件里已有的 L0」；仍禁止删文件里没出现的树，禁止已有 SOP 后用本页种新号。

- 该项目尚无清单（第一次 SOP）→ 整表插入，**每个节点**（L0 与全部子孙）写入 `location` / `vehicle_model` / `bom_version`（抄 snapshot），生失效抄项目起止（结束空则空）。
- 已有 SOP 后，文件中的 L0 库里没有 → **拒绝整单**，文案指向工程变更。不要在本页用切点月种新树。
- 库里已有同号 L0 且仍有效 → 更新该树属性/子孙（仍按现网 Parser），**生失效与 L0 `seq_no` 不动**；新插入的子孙节点仍必须写上基地/项目/版本，生失效抄该树根当前值，`bom_version` 抄该树根当前值。同一 snapshot 同号只有这一棵。
- 文件没有、库里有的 L0 → **留下**。生失效由 §2.2 单条 PATCH 改（级联子树）。

工程变更写入后再收窄：已失效的、以及生效月不是项目 SOP 开始月的 L0 **整棵跳过**（不 `delete_descendants`）。见 §8.2。本期 SOP 不提前改这条。

不要用 snapshot `status=archived` 代替树根失效。

表单已有基地 + 可引入项目。本页 **不出切点年月**。探测到已有 L0 时只切换 §8.1「已有 SOP」文案，不换成设变表单。

### 3.3 读（本切片）

`GET /snapshots/{id}/tree` 与 `GET /snapshots/{id}/nodes` 增加 `year`、`month`、`include_expired`。默认墙钟月、只展开该月命中的 L0 及其子孙。

Service：不过滤子孙行；先收集命中的 L0 id 再收子树。`list_by_snapshot` 全量方法留给下游，不要改成默认 as_of。

`#/bom-structure` 总成卡、`#/bom-viz` 吃过滤后的 tree。VO **每个节点** 必须带 `location`、`vehicle_model`、`bom_version` 与四列生失效；前端不要 join 头表去猜。L1/L2 与树根同值，不要空着。按月命中仍以 L0 为准再收子树（子件时段与根相同，不单独筛掉半棵树）。

---

## 4. 冲压工艺确认

### 4.1 改造

四列加在 `stamping_parts`。工序、拼焊子片跟零件行走，不加列。

**唯一键去掉 `version`，也不要改成生效年月。** UNIQUE：`(location, stamping_supplier, vehicle_model, part_number)`。一个零件一行、一个版本；`version` 列仍在，SOP 抄确认表头，再导已有号 **不改 version**。换号（AA→AB）是 **另一个零件号**，另一行，不是同一号插第二段有效期。

禁止：UNIQUE 含 `effective_year` / `effective_month` / `expiry_year` / `expiry_month`；同一号截断旧行再插新行冒充两段；靠改 `version` 冒充两行。不换号只改工艺：更新 **这一行** 的材料/工序，生失效走 §2.2 PATCH。

有加工费：现网「整包不能覆盖」。改造后不整包删，改为：已有加工费的零件行 **禁止删除**；改失效月不删行、不级联删 `stamping_process_fees`。SOP 页仍不许因文件出现新号而插行（走工程变更）。

### 4.2 写入

`upload/persist/parts.py`：日常导入 **不** 调用 `delete_by_scope`。上传仍只选文件解析范围，**不加切点年+月**。

按 `(location, stamping_supplier, vehicle_model, part_number)` 找 **这一行**（唯一键，至多一行）：

- 该冲压厂在该项目下尚无工艺行（第一次 SOP）→ 整表插入，每件生失效抄项目起止（结束空则空）。
- 已有 SOP 后库里没有这一号 → **拒绝整单**，指向工程变更。
- 有这一号 → 更新材料/工序/子片（沿用现网利废、家模、比例保留规则），**生失效、`seq_no`、`version` 不动**。
- Excel 没有的号 → **不删**。

列表 PATCH 见 §2.2。`POST /parts/batch-delete` **本期不改范围键**（仍可按版本整包删），不要拿它当导入覆盖的替代；有加工费 RESTRICT 照旧。

### 4.3 读（本切片）

`StampingPartQuery` 增加 `year`、`month`。`GET /parts/list` 按查看年+月 as_of 过滤，**不出**「含已失效」开关。版本下拉不再当「这个月用哪包工艺」。列表 VO、详情 VO 带四列。

本切片工艺确认导出 **必须** 带 `year`、`month`（跟列表筛控件同一套，前端给出）。`GET /materials`、零件价 **不动**。

### 4.4 冲压加工费计算：按零件期取件，入口加项目年交集

`#/stamping-process-fee-calc` 与 `POST /api/stamping/process-fees/calc` 仍是 **年度账**（结果表键仍是年，不加月）。取哪些零件，必须问 `stamping_parts` 的生失效，**禁止**再用项目 `require_overlaps_year` / `list_overlaps_year` 当取件 WHERE。身份另问项目档案是否与该年有交集（`require_overlaps_year`，已含基地启用）。

年交集（与 `overlaps_year` 同一套，跨年闭区间）：

```text
零件生效 <= 该年12月  且  （失效空  或  失效 >= 该年1月）
```

| 场景 | 做 |
|------|----|
| 项目已在上年失效，零件失效空 | **不算**。身份 `require_overlaps_year` 不过 |
| 项目该年仍有效（含年中停产仍有交集），零件已失效到上年 12 月 | **不算该件** |
| 零件 8 月才生效 | **算进该年**（年账，不是墙钟月） |
| 该年没有任何零件与年交集 | 硬停：「该年没有有效期内的冲压零件」，不要空算一张表 |

计算就绪件数、级联项目下拉（本页只带年、不带月，与 `list_overlaps_year` 求交）、引擎补算覆盖检查，与计算同一把钥匙。`list_with_processes` / `list_by_location_and_vehicle` **默认仍全量**；加工费路径显式传计算年，零件核价路径显式传计算年+月。

不要：把加工费改成按月结果表；用墙钟月或最近核价月裁件；项目未失效就把已失效零件算进去；用项目期当取件 WHERE。

### 4.5 冲压零件价格计算：按零件期取件，入口加项目月命中

`#/stamping-part-cost-calc` 与 `POST /api/costing/stamping-part-cost/calc` 仍是 **月度账**（结果表键仍是年+月，钢价/废料按该月取）。年+月是 **核价账期**。取哪些零件，必须问 `stamping_parts` 的生失效是否命中该年该月，**禁止**再用项目 `require_introducible` / `list_introducible` 当取件 WHERE。身份另问该账期月是否可引入（`require_introducible`）。

月命中（与列表 as_of 同一套，跨年闭区间）：

```text
零件生效 <= 该年该月  且  （失效空  或  失效 >= 该年该月）
```

| 场景 | 做 |
|------|----|
| 项目已在上月失效，零件失效空 | **不算**。身份 `require_introducible` 不过 |
| 项目该月仍有效，零件已失效到上月 | **不算该件** |
| 零件 8 月才生效 | **7 月不算，8 月算** |
| 该月没有任何零件命中 | 硬停：「该月没有有效期内的冲压零件」，不要空算一张表 |

**不要版本。** 计算页不出版本下拉；入参忽略 `version`。`version` 仍从零件行抄到结果行作展示，不进计算门禁、不分锁。结果 UNIQUE 现网含 `version` 本期不改。

计算就绪件数、加工费是否齐（只问该月命中的零件）、级联项目下拉（本页带年+月，走 `list_introducible`），与计算同一把钥匙。

不要：用墙钟月裁件；把已失效零件算进该月；用项目期当取件 WHERE。

### 4.6 总成核价计算：按节点期取件，入口加项目月命中

`#/assembly-cost-calc` 与 `POST /api/costing/assembly-costs/calc` 仍是 **月度账**（结果表键仍是年+月）。年+月是 **核价账期**。取哪些树，必须问 `bom_nodes` 的生失效是否命中该年该月（**以 L0 为准再收子树**，可跨该基地+项目下多个 BOM 版本），**禁止**再用项目 `require_introducible` / `list_introducible` 当取件 WHERE，**禁止**再要求选定 snapshot / BOM 版本。身份另问该账期月是否可引入（`require_introducible`）。

月命中与 §4.5 同一套：

```text
L0 生效 <= 该年该月  且  （失效空  或  失效 >= 该年该月）
```

| 场景 | 做 |
|------|----|
| 项目已在上月失效，树根失效空 | **不算**。身份 `require_introducible` 不过 |
| 项目该月仍有效，树根已失效到上月 | **不算该棵** |
| 树 8 月才生效 | **7 月不算，8 月算** |
| 该月没有任何 L0 命中 | 硬停：「该月没有有效期内的 BOM 树」，不要空算一张表 |

**不要版本。** 计算页不出版本下拉；入参忽略 `bom_version`。版本仍从节点抄到结果行作展示，不进计算门禁、不分锁。结果 UNIQUE 去掉 `bom_version`：`(year, month, location, vehicle_model, source_node_id)`。计算锁同样是年+月+基地+项目。

计算就绪、焊接覆盖（只问该月命中树上的焊信/拆解）、零件价是否齐（只问该月命中的冲压件）、级联项目下拉（本页带年+月，走 `list_introducible`），与计算同一把钥匙。采购对象从该基地+项目各版本清单里收，再过滤到命中树的 `source_node_id`。

月度引擎同一项目当月 **总成核价一次**（把该月有效期内各版本树算完），不要再按 BOM 版本拆多趟。

不要：指定版本才算半边树；把已失效树算进该月；用项目期当取件 WHERE。

### 4.7 核价引擎：计点 as_of 之后再滤项目月

`#/costing` 与 `POST /api/costing/engine/ready` / `runs` 仍是 **月度编排**（入口仍是基地 + 年 + 月）。年+月是 **核价计点**。数据有效性检查与范围发现先问：

- 冲压零件生失效是否 **命中该年该月**
- BOM L0 节点生失效是否 **命中该年该月**

再留下 `list_introducible(账期年, 月)` 里的项目。**禁止**用项目期当零件/树取件 WHERE。项目该月已失效 → **不进计划**（即使对象失效为空）。as_of 两边都空 → 不能启动，去零件列表 / 产品结构核对有效期。as_of 有件但项目期裁空 → 去项目一览（门禁 code `vehicle_model_period`）。

子计算补算沿用各自计点：冲压加工费 / 模具费 / 焊接费问 **年交集**；零件价 / 总成问 **月命中**。身份：月度 `require_introducible`，年度 `require_overlaps_year`。见 [costing-engine-design.md](../../costing/costing-engine-design.md) §5.1、§6.2。

---

## 5. 模具布点

### 5.1 改造

四列加在 `stamping_die_parts`。工序跟零件走。

**UNIQUE 保持现网，不要改成含生效年月。** `(location, vehicle_model, part_number)`：一个零件一行。`version` / `stamping_supplier` 仍可从工艺回填，**不**当唯一键、**不**当有效期。再导已有号 **不改** 生失效、`seq_no`、已回填的 `version`。换号是另一个零件号、另一行，不是同一号插第二段有效期。

禁止：UNIQUE 含 `effective_year` / `effective_month` / `expiry_year` / `expiry_month`；同一号截断旧行再插新行冒充两段。不换号只改尺寸/工序：更新 **这一行**，生失效走 §2.2 PATCH。

有模具费行引用：禁止删被引用的布点行（库级 `source_die_part_id` `RESTRICT`，文案「仍被冲压模具费引用，请先删除对应模具费后再删」）；改期走 §2.2，不删行。

检具费 **不加列**。不要用布点有效期冒充检具。改图换号时检具费档案 / 模具费结果抄写见 [part-number-revision-design.md](part-number-revision-design.md) §4.3.1 / §4.3.2，不在本文件展开。

### 5.2 写入

`die/upload/service.py`：**去掉** 整项目 `delete_scope`。

第一次 SOP（该基地+项目尚无布点行）：整表插入，每件生失效抄项目起止（结束空则空）。其后按 `(location, vehicle_model, part_number)` 找 **这一行**（唯一键，至多一行）：有则更新尺寸/工序（`alloc_ratio` 仍按零件号+工序号沿用已改值；**生失效、`seq_no`、已有 `version` 不动**）；无这一号 → **拒绝整单**，指向工程变更。Excel 没有的号不删。补号 `DP-40-{项目}-流水` 扫描 **含已失效行已占用的号**，避免复号。

表单已有基地 + 可引入项目。本页 **不出切点年月**。单条改期见 §2.2。`POST /batch-delete` 本期仍整项目，不拿它当导入替代。

### 5.3 读（本切片）

`StampingDiePartQuery` 增加 `year`、`month`。列表按查看年+月命中，**不出**「含已失效」开关。未带月可墙钟。本切片导出 **必须** 带 `year`、`month`（跟列表筛控件同一套，前端给出）。无命中 = 该件该月列表/导出不出现，不用失效行顶上。

### 5.4 冲压模具费计算：按布点零件期取件，入口加项目年交集

`#/stamping-die-fee-calc` 与 `POST /api/stamping/die-fees/calc` 仍是 **年度账**（结果表键仍是年，不加月）。取哪些布点零件，必须问 `stamping_die_parts` 的生失效，**禁止**再用项目 `require_overlaps_year` / `list_overlaps_year` 当取件 WHERE。身份另问项目档案是否与该年有交集（`require_overlaps_year`）。

年交集与 §4.4 同一套（`overlaps_year`，跨年闭区间）：

```text
布点生效 <= 该年12月  且  （失效空  或  失效 >= 该年1月）
```

| 场景 | 做 |
|------|----|
| 项目已在上年失效，布点失效空 | **不算**。身份 `require_overlaps_year` 不过 |
| 项目该年仍有效（含年中停产仍有交集），布点已失效到上年 12 月 | **不算该件** |
| 布点 8 月才生效 | **算进该年**（年账，不是墙钟月） |
| 该年没有任何布点与年交集 | 硬停：「该年没有有效期内的模具布点」，不要空算一张表 |

计算就绪件数、计算页项目下拉（只带年、不带月；`/die-fees/filters?for_calc=1` 与 `list_overlaps_year` 求交）、共模继承扫描，与计算同一把钥匙：只扫该年有效期内布点（`id` 升序）。`list_with_processes` **默认仍全量**；模具费路径显式传计算年。结果一览默认路径不要走 `for_calc`。

不要：把模具费改成按月结果表；用墙钟月或最近核价月裁件；项目未失效就把已失效布点算进去；共模扫描仍带上年已失效件；用项目期当取件 WHERE。

---

## 6. 焊接工艺拆解：期跟节点走

拆解不算年账、没有计算年字段。**生失效的唯一真相是 `bom_nodes`。** 拆解行用现成的 `source_node_id` 去取，**禁止**在 `bom_welding_process_breakdown_node` 再落四列。这样 BOM L0 改期级联子树后，焊接费不必再生成拆解才看见新期。

和采购对象同一纪律：派生表不复制时段。焊接费取件：

```text
拆解行 INNER JOIN bom_nodes ON source_node_id = bom_nodes.id
树根 = level==0；树根 overlaps_year(year) → 收下整棵子树
实现：``period_trees.nodes_in_year_overlap_trees``；对外 ``BomPeriodService.node_ids_overlapping_year``
月命中：``period_trees.nodes_in_as_of_trees``；对外 ``BomPeriodService.list_as_of_trees``
```

**禁止** join `bom_snapshots` 问期（头上无这四列），也 **禁止** 用项目 `require_overlaps_year` 当取件 WHERE，也 **禁止** 用 L1/L2 本行生失效筛期。四年后改树期口径只改 `period_trees`。

切片正文：[焊接工艺拆解](../../bom/welding-process-breakdown-design.md)。焊接费计算已按 §6.3 落地。

### 6.1 拆解行上有什么、没有什么

| 分组 | 字段 | 说明 |
|------|------|------|
| 范围 | `location`, `vehicle_model`, `bom_version` | 现网已有。**拆解生成**找包 / 锁用 snapshot 头。行上 `bom_version` **抄所属 L0 树根**（列表/UNIQUE 认树根，不认 SOP 头）。`location` / `vehicle_model` 从 source 节点抄 |
| 溯源 | `source_node_id` | 取期的钥匙。必须能命中 `bom_nodes.id` |
| 溯源 | `snapshot_id` | 辅助；不是身份、不是取件钥匙 |
| 时段 | （不落表） | 读 source 节点四列 |

`bom_welding_process_breakdown_line` 也不落四列。生成日志、锁范围仍是基地+项目+版本，不加年。

**UNIQUE 保持现网。** `(location, vehicle_model, bom_version, source_node_id)`，本来就不含生失效。不要为了「两段期」去改 UNIQUE、也不要同一 source 插第二行。

禁止：拆解表加 `effective_*` / `expiry_*`；拆解行 PATCH 生失效；LEFT JOIN 节点拿空期当成「未结束」。

### 6.2 取期

```text
bom_welding_process_breakdown_node.source_node_id  =  bom_nodes.id
再沿 parent_id 找到该树 L0 树根
```

**年交集只问 L0 树根四列**，与总成核价「命中 L0 再收子树」同口径。L0 / L1 / L2 拆解行都先定位 source，再爬到树根；**禁止**用 L1/L2 本行生失效筛期。子孙列设计上应与树根同值（§3.1），但工程变更后若 L1 失效空、树根已截断，问本行会漂进旧树——必须以根为准，不能漂。

不要问项目档案、不要墙钟月、不要从 snapshot 头猜。

`source_node_id` 为空、节点已删、或爬不到 L0：该拆解行 **不参加** 年交集，须再生成。重导材料清单会换 `bom_nodes.id`，现网本就要再生成拆解，这条继续成立。

范围三列：`location` / `vehicle_model` 从节点抄；`bom_version` 抄所属 L0 树根（生成找包仍用 snapshot 头；列表/UNIQUE 认树根）。它们改得少；**时段会经 §2.2 PATCH 独立变**，所以只 join、不抄。

### 6.3 `#/bom-welding-fee-calc`：年 + 基地 + 项目

跟冲压加工费 / 模具费同一把钥匙。**入参只有：**

```text
year, location, vehicle_model
```

**不要** `bom_version`，**不要** `snapshot_id`，**不要**选层级。计算页不出版本下拉；项目下拉只带年、不带月。身份 `require_overlaps_year`（账期年）。取件按 **L0 树根** 年交集，**禁止**用项目期当取件 WHERE，**禁止**用 L1/L2 本行期。一次算拆解里出现过的全部 level。

必须先有 [焊接工艺拆解](../../bom/welding-process-breakdown-design.md) 列表，**禁止**再扫 `weld_info` 认人：

```text
该基地 + 该项目 的全部拆解行（不按版本过滤）
  INNER JOIN bom_nodes ON source_node_id = bom_nodes.id
  树根 = level==0；树根 overlaps_year(year) → 收下整棵子树
  实现：app/repositories/bom/period_trees.py
```

```text
树根生效 <= 该年12月  且  （树根失效空  或  树根失效 >= 该年1月）
```

| 场景 | 做 |
|------|----|
| 同一项目两份版本 / 两棵树，树根都与该年有交集 | **都算**（年账；含各树 L0/L1/…） |
| 项目已在上年失效，树根失效空 | **算**（身份另过；取件仍问树根） |
| 树根已失效到上年 12 月，L1 失效仍空 | **整棵不算**（含该树全部拆解行） |
| 树根 8 月才生效 | **算进该年** |
| 从未生成拆解 | 硬停：先去焊接工艺拆解生成 |
| 有拆解但树根年交集后零行 | 硬停：「该年没有有效期内的焊接拆解」，不要空算一张表 |

`bom_welding_fees` 仍是 **年度账**（结果键仍是年，不加月）。结果行可 **抄** 拆解上的 `bom_version` 作溯源展示，**不是**计算门禁、**不进**新唯一键。锁范围改为 **年 + 基地 + 项目**（一次算完该项目该年所有命中树）。

不要：join snapshot 问期；按 L1/L2 本行生失效筛期；计算页选手选版本；没有拆解还去扫 BOM；把焊接费改成按月结果表。

---

## 7. 迁移

存量 `bom_nodes`：从所属 snapshot 抄 `location` / `vehicle_model` / `bom_version`；生失效与第一次 SOP 相同，抄该行所属 `vehicle_models` 的开始月与结束月（项目结束空则失效空）。工艺行、布点行只补生失效四列（它们现网已有基地/项目；工艺已有 version）。

存量拆解节点 **不补四列**。取期靠现成 `source_node_id` join `bom_nodes`。source 已不在则再生成，禁止猜项目档案、禁止墙钟月。

上线前扫描：

1. 同一 snapshot 两个 L0 同零件号。
2. `stamping_parts` 去掉 version 身份后，同厂同项目同号多行（不同 version）→ 一个零件只能一行，人工合并，禁止静默删。
3. 布点同项目同号本就 UNIQUE，一般无重复。

有冲突：人工截断时段或合并，禁止静默删行。两份 `bom_version` 头并存：不自动合并。本期列表 as_of 按 **当前打开的那份 snapshot** 过滤 L0；跨头双命中留到下游一期再处理。

---

## 8. 界面（三页同一习惯）

产品结构（总成卡 + 结构图）、冲压零件列表、模具清单：筛年、月；默认过滤命中。点导出时前端把 **当前筛到的** `year`、`month` 放进请求，禁止只点按钮不带参。以后工程变更倒出当月数据同一纪律。

**列表必须能看见时段。** 不要只放详情里。绑定 `effective_year/month`、`expiry_year/month`，展示走 `fmtPeriod`（`2026年07月`）。失效空显示「未结束」，不要空白得像没做。不要日历日、不要只显示年。BOM 树节点还要同时看见基地、项目、版本（见下表）。

| 列表 | 谁出范围与时段 |
|------|----------------|
| 产品结构总成卡 / 结构图 | **每一个节点**：基地、项目、版本、生效日期、失效日期。L1/L2 与树根同值，不要空格。改期只在 L0 |
| 冲压工艺零件列表 | 每一零件行（现网已有基地/项目/版本；补生效/失效） |
| 模具布点零件列表 | 每一零件行（现网已有基地/项目；版本可空回填；补生效/失效） |
| 材料清单列表（snapshot 头） | **不出** 节点上的生失效（头上无这四列） |

列表/树 VO 必须带这些列，前端不要自己猜。BOM 节点顺序：基地、项目、版本，然后先生效、后失效。工艺/布点列放在零件号/名称附近，同一顺序：先生效、后失效。

**单条编辑**（总成卡 / 结构图 L0 / 零件详情抽屉）：生效、失效都可改、都要能保存，走 §2.2。权限与现网该对象 `update` 同一级。L1/L2 **展示** 基地/项目/版本/生失效，**不出现** 可改控件。节点上的基地/项目只读，禁止 PATCH 改这两列。节点 `bom_version` 本期也不经界面改（SOP 抄头）；工程变更种新树时再写变更字，仍不走本页 PATCH。

不要用「BOM 版本」「工艺版本」下拉代替月份。

### 8.1 上传页：这是 SOP，投产后走工程变更

三页同一习惯（`#/bom-upload`、`#/stamping-upload`、`#/stamping-die-upload`）。**本页不是设变入口。** 切点年+月、新旧改图、工程变更 Excel 只属于 [工程变更](part-number-revision-design.md)，不要做进这三页。工程变更菜单即使未上线，也 **禁止** 在 SOP 页用切点控件顶替。

页顶固定说明（三页同一句，可按对象换成「材料清单 / 工艺确认表 / 模具布点」）：

> 本页只导入 **SOP**（该项目第一次标准化投产）。投产使用后改图、新旧并存，必须走 **工程变更**，不要在本页操作。

第一次 SOP（该块尚无行）：只读展示「本文件按项目 SOP 时段：{`fmtPeriod` 开始} – {结束空则「未结束」}」。时段来自项目档案，本页不能改。提交钮可用。

已有 SOP：切到第二段说明，**仍不出切点月**：

> 该项目已有 SOP。再导只更新文件里已有对象的属性，不会删除未出现的行。文件里出现新号将整单拒绝。改图请走工程变更。

硬停文案（文件含 SOP 里没有的总成/零件号）：「该项目已有 SOP，不能在本页新增。改图请走工程变更。」不要改成「请填写切点年月」。

工艺上传仍不选手选基地项目；说明挂在选文件上方，与另外两页同一句。

---

## 8.2 给工程变更留的口（本期必须写对）

工程变更作业见 [part-number-revision-design.md](part-number-revision-design.md)。本期 **不实现** 工程变更菜单，但表和写入契约要让它能接上，不要返工改列。

**已经够用**

| 工程变更要用 | 本期 |
|----------|------|
| 同一 snapshot 里 AA、AB 两棵树 | L0 UNIQUE `(snapshot_id, part_number)`，**不含** 生失效；AA/AB 是两个号。不新建 D/10 |
| 旧根失效到切点前一月、新根从切点起 | 四列 + 相邻月合法；L0 PATCH 级联子树 |
| 工艺/布点未出现的不删 | 导入按号对齐，去掉整包删。三块 UNIQUE **都不含** 生失效 |
| SOP 三页不再当设变入口 | §8.1 拒绝新号，文案指向工程变更 |
| 列表 7 月见 AA、8 月见 AB | 本切片 as_of |
| 工程变更/本切片导出按月 | 导出 API 必填 `year`+`month`，前端给；缺参 422，不默墙钟 |
| 过期布点占用的模具编号不复号 | 补号扫描含已失效行 |
| 3096AA 同时挂在旧树和新树 | UNIQUE 只约束 L0；L1 同号可多行，各跟各的树根时段 |

**本期必须定死，否则工程变更会卡住**

1. **插入走同一套 Write。** `BomNodeWrite` / 工艺零件插入 / 布点零件插入必须含基地、项目、版本、生失效（BOM 节点还含 `seq_no`）。SOP 上传、以后的工程变更都调这套，不要把列只写在 upload 闭包里。工程变更种树 = 同一事务里：PATCH 旧 L0 失效到切点前一月 → insert 新树（生效=切点、失效抄项目结束月、`seq_no`=旧根）。不要走 `BomNodeService.create_node`（强制节点版本=头）。SOP 上传不走「新号」分支。
2. **有采购对象 / 焊接拆解不挡插新 L0。** `assert_bom_scope_unused` 只拦删 snapshot / 整包覆盖，不拦种树。工程变更写入后下游行已经在。
3. **节点 `bom_version` 允许与头不同。** SOP 抄 D/09；工程变更新树写变更字，头仍 D/09。不要 CHECK / Service 断言行版本 = 头版本。**snapshot 只约束拆解生成（SOP 那一包）；焊接费计算和列表一样认树根，不认 SOP 头。** 拆解 / 焊接费行的 `bom_version` **抄所属 L0**，不要抄 snapshot 头。
4. **`seq_no` 冻结。** SOP 第一次写入后，三块再导已有对象不得改 `seq_no`。工程变更 AB 继承 SOP 槽，不在本期做继承算法，但槽不能被再导冲掉。
5. **同一 `seq_no` 撞月按事务结束状态校验。** 工程变更先截断旧根再生效新根；不要在截断前就因「将要插入的月」把整单打回去。生失效不进 UNIQUE。
6. **子孙列有值 = 跟树根，不是独立切点。** 工程变更正文若写「子孙不写生失效」，意思是不独立改期；落库仍每个节点都写同值（与 §3.1 一致）。
7. **导出必带年月。** 工程变更倒出当月树/工艺/布点，以及本切片同类导出：`year`、`month` 由前端给出，跟页上筛控件同一套。缺参 422。空模板下载除外。
8. **工程变更写入后才改 SOP 再导门禁。** 已失效 L0、以及生效月不是项目 SOP 开始月的 L0 整棵跳过，不 `delete_descendants`。本期 SOP 仍按 §3.2 重建文件里出现的有效树子孙。不要为此改 Parser。

**不是本期缺口（工程变更自己做）**

工程变更 Excel / 变更头 / 按树对齐换号 / `seq_no` 继承写法 / 采购对象插行抄确认 / 焊接拆解从旧树结果抄到新树（主表+全部明细，禁止按焊信重拆；行上 `bom_version` 抄树根）。核价与引擎 as_of **已落地**。拆解生成找包仍用 SOP 头；Parser **不改**。工程变更写入只收窄三条整包写入门禁，见 [工程变更 §4.6](part-number-revision-design.md)。

---

## 9. 本文不做

| 不做 | 说明 |
|------|------|
| 采购对象 / LLM 就绪按月裁树 | 总成核价与引擎发现已按节点/零件月命中。`list_by_snapshot` 全量读法仍给结构页等 |
| 采购对象列表默认按月 as_of | **否决。** 列表是档案：默认包含已过期；生失效 join 树根一列；对象行仍不落四列。见 [采购对象 §14](../../bom/bom-procurement-objects-design.md) |
| 拆解结果表补生失效四列 | **否决。** 期 join source 节点，见 §6 |
| 零件用在哪 as_of | 仍按整份 snapshot |
| 工艺批量删改键、布点批量删改键 | 本期导入不再走它们；管理删除可暂留现网 |
| 工程变更菜单、工程变更 Excel、变更头自动种树 | [part-number-revision-design.md](part-number-revision-design.md)。SOP 三页不做切点月、不种新号 |
| AB 继承 SOP 序号、设变给新树插采购对象并抄确认 | 同上 |
| 一口价/焊接单价年内分段 | **已否决。** [effective-period-design.md](../../costing/effective-period-design.md) |
| 取价 AB 回退 AA；库内复制出新号 | 否决 |

本期 SOP 三页只负责第一次投产导入，以及之后对 **已有号** 的属性再导（不删未出现的行）。改图路径等工程变更。列表仍可单条改期（纠错 SOP 时段），不要当成设变作业。冲压加工费 / 模具费 / 焊接费计算已接零件（布点、节点）年交集；冲压零件价格 / 总成核价 / 引擎发现已接月命中。

---

## 10. 验收

1. 项目尚无清单/工艺/布点时第一次导入：行上生效=项目开始月，失效=项目结束月；项目结束空则行上失效空。不得写成墙钟月。
2. 零件/树根/布点详情打开，改生效或失效（含清空失效）能保存；失效不得早于生效。同一 snapshot 同一 `seq_no` 两棵 L0 撞月被拒绝。再导 Excel 不会把这次改期盖掉。
3. 三页上传顶栏都写清「本页只导入 SOP；投产后改图必须走工程变更」。已有 SOP 后再打开，不出现切点年月控件。
4. 再导一份只含部分 **已有** 总成的材料清单，其它 L0 还在。
5. 再导工艺确认（部分 **已有** 件），3096AA 还在。
6. 再导布点（部分 **已有** 件），未出现的布点行还在。
7. 已有 SOP 后文件里出现新号：整单拒绝，提示走工程变更（不要提示填切点月）。
8. 结构总成卡、结构图 **每个节点** 都能看见基地、项目、版本、生效日期、失效日期；L1/L2 与树根同值，不要空。工艺列表、布点列表看见生效/失效；失效空为「未结束」。材料清单头列表没有节点这几列。
9. 库内任意 `bom_nodes` 行：`location` / `vehicle_model` / `bom_version` / `effective_year` / `effective_month` 非空；失效两列同空或同有；与所属 snapshot 的基地/项目一致。SOP 行 `bom_version` 与头相同；工程变更新树节点可以写变更字，头仍 SOP（见 §8.2）。
10. 本切片工艺确认 / 布点导出：请求带当前列表的年+月；缺年或月 422。7 月导出不见已失效到 6 月的件。
11. 冲压加工费计算 2026 年：不含已失效到 2025-12 的零件；含该年 8 月才生效的零件。项目与 2026 年无交集 → 入口拒绝。项目 2026 年中停产但仍有年交集 → 身份过，取件仍按零件年交集。入口不再把项目期当取件 WHERE。
12. 冲压模具费计算同一套：2026 年不含已失效到 2025-12 的布点；含该年 8 月才生效的布点。项目与该年无交集 → 入口拒绝。共模只在该年有效期内布点之间继承。
13. 焊接费计算页只有年+基地+项目，不出版本、不选层级，一次算全部层。2026 年不含已失效到 2025-12 的拆解节点；含该年 8 月才生效的节点。没有拆解则硬停。项目与该年无交集 → 入口拒绝。
14. 冲压零件价格计算 2026-07：不含已失效到 2026-06 的零件；不含 8 月才生效的零件；含该月仍有效的零件。项目 6 月停 → 7 月身份拒绝。不出版本。列表 as_of 仍可见停产项目下的活件（查询，不是计算）。
15. 总成核价计算 2026-07：不含已失效到 2026-06 的 L0 树；不含 8 月才生效的树；含该月仍有效的树（可跨版本）。项目 6 月停 → 7 月身份拒绝。不出版本。
16. 核价引擎 2026-07：项目 6 月停、零件或 L0 仍命中 7 月 → 不进计划，文案去项目一览（`vehicle_model_period`）。该月没有任何命中零件/树 → 不能启动，文案去零件列表 / 产品结构。项目期内且有件 → 仍进计划。

本期 **不验收**：在 SOP 三页完成 3086AA→AB 改图；采购对象跟月、反审重算。改图走工程变更。

---

## 11. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-16 | 现网改造专稿：BOM 树根、冲压零件、模具零件三块并列；停整包覆盖。 |
| 2026-09-16 | 第一次导入=项目 SOP：生失效抄项目起止；项目结束空则行上失效空。 |
| 2026-09-16 | 单条编辑 update 必须能改生效、失效；导入不覆盖已改时段。 |
| 2026-09-16 | 前端列表固定列：生效日期、失效日期；展示走 `fmtPeriod`。 |
| 2026-09-16 | **收窄本期：** 只改三块自身（表、导入对齐、PATCH、列表/树 as_of）。核价 / 采购对象 / 引擎不动。先写现网写入与列表入口。 |
| 2026-09-16 | 三页上传写明只做 SOP；投产后改图必须走工程变更。SOP 页不出切点月、不种新号。 |
| 2026-09-16 | BOM 每个树节点必须有基地、项目、版本、开始年月、失效年月；子孙与树根同值，改 L0 级联子树。 |
| 2026-09-16 | 给工程变更留口：Write 可插树、下游不挡新 L0、节点版本可与头不同、`seq_no` 再导不改。 |
| 2026-09-16 | 冲压零件 UNIQUE 去掉 version，也不含生效年月：`(location, stamping_supplier, vehicle_model, part_number)`；一个零件一个版本。 |
| 2026-09-16 | 布点 UNIQUE 同样不含生效年月：保持 `(location, vehicle_model, part_number)`；一个零件一行。 |
| 2026-09-16 | 生失效永远不进 UNIQUE。BOM L0 改为 `(snapshot_id, part_number)`。 |
| 2026-09-16 | 工程变更及本切片同类导出必须带 year+month，前端给出；缺参 422，不默墙钟。 |
| 2026-09-16 | 冲压加工费取件按零件年交集；身份仍问账期 `require_overlaps_year`。 |
| 2026-09-16 | 冲压模具费取件按布点年交集；身份仍问账期 `require_overlaps_year`。 |
| 2026-09-16 | 冲压零件列表、模具清单不提供「含已失效」；只靠查看年+月命中。 |
| 2026-09-16 | 拆解结果表 **不** 存生失效。期用 `source_node_id` join `bom_nodes` 再认 L0 树根。焊接费计算入参年+基地+项目，跟拆解列表、按树根年交集；不靠版本/snapshot。已落地。 |
| 2026-09-16 | 冲压零件价格取件按零件月命中，不靠版本；身份问账期 `require_introducible`。 |
| 2026-09-16 | 总成核价取件按节点月命中，不靠 BOM 版本；身份问账期 `require_introducible`。 |
| 2026-09-16 | 核价引擎发现先对象 as_of，再 `list_introducible` 裁项目月；空名单分无件 vs 项目停。 |
| 2026-09-16 | 计算入口加项目账期帽子：月度 `require_introducible`、年度 `require_overlaps_year`；取件仍问对象期。 |
| 2026-09-16 | 焊接费计算页不选层级，始终算拆解全部层。 |
| 2026-09-16 | 工程变更对照现网：SOP 再导已失效 L0 整棵跳过；拆解行 `bom_version` 抄 snapshot 头；新树失效抄项目结束月。 |
| 2026-09-17 | SOP 再导同时跳过工程变更种的树（生效月≠项目 SOP 开始月），避免重建 AB 子孙。 |
| 2026-09-17 | 收口：跳过工程变更树 / 生成页拒绝整包 / 引擎 generate 被同一钥匙拦住，都是 **工程变更写入后** 才生效；本期 SOP 写入保持现网。Parser 不改。 |
| 2026-09-18 | 采购对象列表：否决默认按月 as_of；默认包含已过期；对象行仍不落四列、join 树根。见采购对象 §14。 |
| 2026-09-18 | 文首「本期仍不动：采购对象」改为已落地口径；与采购对象 §14 / 工程变更插行现网对齐。 |
| 2026-09-18 | 焊接费取件改为 L0 树根年交集；禁止用 L1/L2 本行生失效筛期（防工程变更后子孙失效空漂进旧树）。 |
| 2026-09-20 | **口径写死：** snapshot 只约束拆解生成（SOP 那一包）；焊接费计算和列表一样认树根，不认 SOP 头。拆解/费行 `bom_version` 抄 L0。 |
