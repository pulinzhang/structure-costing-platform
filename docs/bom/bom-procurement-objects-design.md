# 采购对象清单 — 设计说明

> **状态：分类 / 生成 / 确认 / 审核 / 列表档案（§14）/ 设变插行 / 生成门禁已落地。**  
> **列表 / 批量取件口径（对齐协议）已落地：** 范围=基地+项目；**必须爬到树根**（§0.1）；`bom_version` 可选=L0 字；禁止用版本找清单头。  
> **生成页写死：只读 snapshot（SOP）。** 版本下拉 / 取件只认 `bom_snapshots`；**后续一律走工程变更**插行，禁止生成页补 `EC-*` 树。  
> **「版本」三义（四年后仍只认这张表，勿混）：**

| 叫什么 | 落在哪 | 谁用 | 谁禁止用 |
|--------|--------|------|----------|
| **snapshot 头 / SOP 字** | `bom_snapshots.bom_version`（如 `D/09`） | **生成页 / 供应商批传** `get_by_unique_key` | 列表/批量/协议取件 WHERE；当「设变版本」 |
| **树根版本字** | 爬到的 `L0.bom_version`（可为 `EC-202505`） | 列表/批量/协议 **浏览筛** | 生成页 / 供应商批传下拉与取件；当清单头键 |
| **清单头冗余字** | `bom_procurement_object_lists.bom_version`（抄 snapshot 头） | 展示/日志副本 | **列表/批量/协议**取件 WHERE / 浏览筛真相 |

与[协议](../costing/procurement-contract-report-design.md) §0.1 / §2 **同一词典**。  
> **列表 §14：** 默认包含已过期；生失效一列只认所属 L0 树根；筛「是否指定供应商」；不含已过期相对墙钟本月问树根。  
> **设变：** 工程变更种树同一事务 `insert_for_new_tree`；`snapshot_blocks_full_generate` 已挡整包 generate（失效树根或生效月 ≠ SOP 开始月 → 409）。  
> **主数据对齐：** 列表基地筛 `expand_for_query`；生成找 snapshot = `require_enabled` + `normalize_vehicle_model` + 规范名精确匹配（干净库不 expand 历史别名），见 §13。指定合同对方见独立设计。  
> 切片：**`bom`**。生成时只读 `bom_snapshots` / `bom_nodes`，写入本切片采购对象表与生成日志。  
> 界面：**项目**。库字段：`vehicle_model`。  
> 取件对齐：[procurement-contract-report-design.md](../costing/procurement-contract-report-design.md) §0.1 / §2（基地+项目；**必须爬到树根**；版本可选=树根版本字，不是 snapshot 键）。  
> 基地：[location-design.md](../masterdata/location-design.md)。项目：[vehicle-model-design.md](../masterdata/vehicle-model-design.md)。  
> 样本：`excel_sample/T13J项目车身件材料清单 (1).xlsx`（T13J · D/09）。  
> 树根有效期见 [bom-process-die-effective-period-design.md](../engineering-change/design-change/bom-process-die-effective-period-design.md)。**有效期只认所属 L0 树根四列**；对象行 **不落** 生失效；禁止用 source 节点自身四列、项目期、清单头当对象时段（与焊接拆解同一纪律：join 取期，不抄）。**列表是档案台账**：默认包含已过期，不按年+月裁；生失效一列 = 所属树根。**核价 / 签约 / 引擎**仍按账期月命中树根。设变增量带出见 §14、[工程变更](../engineering-change/design-change/part-number-revision-design.md) §4.4。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)；引用保护见宪法 **§4.3**。

**对人展示 vs 内部码。** 页面、生成摘要、Excel 单元格用中文（退化供货件、分总成、冲压件、标准件/胶等）。库字段、API、分类函数仍用 `l0_degenerate` / `other_leaf` 等码。Excel **工作表名**不能含 `/`，标准件分区表名用「标准件及胶等」。

### 改前必读（不变量；违反即回归）

1. **对象行不落生失效四列。** VO 的 `effective_*` / `expiry_*` 只来自所属 L0 树根（**爬到树根** / `map_l0_periods` / join）；禁止加 ORM 列、禁止读 `source_node_id` 自身四列当真相。  
2. **列表是档案。** 默认 `include_expired=true`；禁止给列表 API 加 `year`/`month`。不含已过期 = 墙钟本月问**爬到的 L0**。批量审核/反审/删除 **不过期筛**。  
3. **列表 expand vs 导出精确。** 列表 `locations`=`expand_for_query`；导出 `location` 精确匹配。  
4. **设变插行。** `insert_for_new_tree` 不删旧行；抄确认/厂家、**不抄** `audit_status`（`row_write` 始终 pending）；配对同号或 `sort_no`，**禁止**字母版本同茎。  
5. **写路径共用。** 生成与插行只经 `row_write.build_object_row_write`；子树用 `app.services.bom.bom.trees.collect_subtree`（公开符号）。  
6. **生成页只读 snapshot（SOP）。** 写：`require_enabled` + `normalize_vehicle_model` + `get_by_unique_key`，版本 = **`bom_snapshots.bom_version` 头字**（如 `D/09`）。只读该 snapshot 下节点做整包分类覆盖。**后续全部走工程变更**（`insert_for_new_tree`）；种树后 `snapshot_blocks_full_generate` → 409，生成页不再补树。**禁止**生成页用 L0/`EC-*` cascade、禁止按节点版本字找树、禁止「只补该月」。prep 同 normalize，不强制 `require_enabled`。**禁止**生成路径 `expand_for_query`。  
7. **列表 / 批量 / 导出取件 = 基地 + 项目。** 用 `list_objects_by_location_vehicle` / `list_lists_by_location_vehicle`。**对象行凡问期、问版本字：必须先爬到所属 L0**（沿 `parent_id` 上溯到 `level=0`；爬不到不出 / 不进筛）。`bom_version` **可选**：有值时只筛 **爬到的 L0** 的 `bom_version` 字，**不是** source 本行、不是清单头键、不是 snapshot 键。**禁止** `get_list_by_scope(基地,项目,版本)` / 用 cascade 的 EC 字去找清单头。与[协议](../costing/procurement-contract-report-design.md) §0.1 同形。  
8. **供应商批传与生成页同一把钥匙、同一套级联：** 前端共用 `snapshot-cascade.js` → BOM 上级域 `GET /api/bom/filters/cascade?version_source=snapshot`；取件共用 `snapshot_scope.require_snapshot` → `get_list_by_snapshot_id`。**禁止**在采购对象域再挂 cascade 路由 / 默认 L0（会露出 EC）。  

---

## 0.1 铁律：必须爬到树根（与协议同一把钥匙）

用语与有效期设计、[协议 §0.1](../costing/procurement-contract-report-design.md) 对齐：写 **「爬到树根」**，不要另造「归属查找」。

| 写死 | 禁止 |
|------|------|
| **取件范围 = 基地 + 项目**；行从该范围清单来（`list_objects_by_location_vehicle`） | 用 `bom_version` 解析 snapshot / 清单头定范围；`get_list_by_scope(基地,项目,版本)` 当取件 WHERE |
| **对象问期 / 问版本字：先爬到所属 L0**，再读树根四列或树根 `bom_version` | 用对象行 / L1 / L2 / source 本行的生失效或版本字当真相 |
| **爬不到 L0 → 该行不进版本筛命中、生失效列空、不含已过期时不出** | 本行四列凑合展示或当筛条件 |
| 版本下拉有值 → 只认 **L0.bom_version** | 用清单头 `bom_version`（SOP 字）或 source 节点字绕过爬树 |
| 生失效列 / `include_expired` → 只认爬到的 L0 四列（§14） | 项目期、清单头、墙钟当对象时段 |
| 生成页 **只读 snapshot（SOP）**；版本 = snapshot 头；整包覆盖只服务投产清单 | 生成页读节点 `EC-*`、用材料清单表头版本找树、设变后仍点生成补行 |
| 供应商批传与生成页同钥：`get_by_unique_key` → `get_list_by_snapshot_id` | 供应商批传「全部版本」/ L0/`EC-*` cascade / 按树根浏览裁 |
| 设变后增量 **只走工程变更**插行 | 在生成页「只补该月 / 只补 EC 树」 |

```text
基地 + 项目
  → list_objects_by_location_vehicle
  → 每行：爬到所属 L0（level==0）
  → 可选版本：L0.bom_version == 下拉字
  → include_expired / 生失效列：只问该 L0 四列
```

对照例：芜湖 T13J + 版本=`EC-202505` → 只出爬到的 L0 版本字为 `EC-202505` 的对象行（设变新树）；**不要**因清单头仍是 `D/09` 报「尚未生成」。选全部版本 → SOP+设变档案全貌（仍每行能爬到 L0）。

## 0. 一句话

**清单定集合。** 一版材料清单对应一份 **采购对象清单**：按树结构列入退化供货件、分总成、冲压件，检测后落库，供采购核对并确认外发/自制。

「生成」是动作（从树上把该列入的节点写成清单）。本文回答 **谁是采购对象**。指定合同对方见 [bom-procurement-object-supplier-design.md](bom-procurement-object-supplier-design.md)；按月应成本签合同见 [procurement-contract-report-design.md](../costing/procurement-contract-report-design.md)。列入规则仍不管价。

```
基地 ★
  └── 项目
        └── bom_snapshots     ← 项目直接下一跳（复合 FK）
              └── 本文清单头   ← 挂 snapshot CASCADE；不是项目下一跳
                    └── 清单行
```

生成不是传 BOM，也不立项。没有材料清单：停止，去焊接工程上传。没有基地 / 项目：去主数据页，本切片不代建。

---

## 1. 业务是什么

交主机厂的是 **供货总成（至少有一个一级件带内部号的 L0）**。采购要管的不是这层容器，而是能单独向二级买、且能在 ERP 对上号的一级件，以及「成品就是一张板」的退化供货件。

| 列入采购对象 | 树上的样子 | 对人展示 |
|--------------|------------|----------|
| 退化供货件 | **仅 L0**。没有子件；**或**全部 L1 都没有内部号 | 退化供货件 |
| 分总成 | L1 **有内部号**，下面有 L2（所属 L0 不是退化供货件） | 分总成 |
| 冲压件 | L1 **有内部号**，下面没有孩子，且是板料（所属 L0 不是退化供货件） | 冲压件 |

L0 永不因 L2 带内部号而变成结构化总成：只看一级件。退化供货件名下的 L1 / L2 **不单独列入**。L2 跟在分总成下，**不单独列入**。L1 **没有内部号** 不是采购对象，进 **核对区（标准件/胶等）**，例如芜湖 T13J 的 `FQ114D0612T21F19E`（弧焊焊接螺柱与盖形螺母组合件）、`B11-4102613`（点焊胶）。

主机厂不允许把带内部号一级件的 L0 整层外发：**这类 L0 永不列入采购对象**。备注写了「凸焊总成供货」也不列入，只进 **核对区（异常）**。全部 L1 无内部号的 L0 按退化供货件列入，不进异常。

---

## 2. 分类规则（列入靠结构 + 一级件内部号）

子节点 = 同 snapshot 下至少一行 `parent_id = 本节点.id`。  
有内部号 = `internal_number` 去空白后非空。  
**一物一码在材料清单上传时已拦**（`validate_internal_number_uniqueness`）：有内部号的行，同一零件号只能对应一个内部号，同一内部号只能对应一个零件号；生成清单不要再写第二套闸。空内部号不参与（标准件/胶等）。

**退化供货件只针对 L0**，不针对 L1 / L2。

| `object_kind` | 条件 | 对人展示 |
|---------------|------|----------|
| `l0_degenerate` | `level=0`，且无子节点 **或** 全部 **L1** 都没有内部号（不看 L2） | 退化供货件 |
| `l1_subassembly` | `level=1`，**有内部号**，且有子节点，且所属 L0 **不是** 退化供货件 | 分总成 |
| `l1_stamping` | `level=1`，**有内部号**，无子节点，且是板料冲压件（§3），且所属 L0 **不是** 退化供货件 | 冲压件 |

| 不列入采购对象 | 落库 `section` | 对人展示 |
|----------------|----------------|----------|
| `level=0` 且至少有一个 L1 带内部号 | 默认不落行；备注含委外话术 → `anomaly` | 异常 |
| 退化供货件名下的 L1 / L2 | 不落行 | — |
| `level=2` | 不落行 | — |
| L1 没有内部号（所属 L0 非退化） | `other_leaf` | 标准件/胶等 |

列入 **禁止** 看：焊接原文有无、备注关键词、年度零件价有无行。这些最多当行字段或告警。L1 内部号 **决定** 该级是否采购对象，并决定 L0 是否退化。

---

## 3. L1：有内部号才可能是采购对象

无内部号的 L1 **一定不是** 采购对象（进核对区），不论名称像不像冲压件。T13J 例：`FQ114D0612T21F19E` 弧焊焊接螺柱与盖形螺母组合件、`B11-4102613` 点焊胶。

有内部号的 L1 叶子再把 **板料** 和 **标准件 / 胶 / 塑料** 分开：

认 `l1_stamping`（顺序，命中即停）：

1. `node_role = make`
2. `thickness_mm` 非空
3. 现网 `resolve_manufacturing_category(...) == "stamping"`

有内部号且不是冲压件的 L1 叶子 → `section=other_leaf`。T13J 叶子焊接原文为 0，**不能**用焊信当冲压件条件。

---

## 4. 退化供货件：全部列入，再标亚类

满足 §2 的 L0 **全部** `section=object` 且 `object_kind=l0_degenerate`（无任何子件，或全部 L1 无内部号）。树上可以有孩子，孩子 **不** 再列入采购对象。亚类只读，不改变是否列入：

| `degenerate_subtype` | 对人展示 | 规则（看原文，不编工艺） | T13J |
|----------------------|----------|--------------------------|------|
| `special_process` | 特殊工艺 | `weld_info` 或 `remark` 含电泳 / 面积 / 黑漆 / 喷粉 / 电镀 | 6 |
| `stamping_blank` | 冲压毛坯 | 其余 | 8 |

无工艺 ≠ 电泳，也 ≠ 不列入。外发还是自制，用行上的 `confirm_status`。生成摘要列出两个亚类件数；冲压毛坯可发货，无焊信则不编处理费，不因此否决检测。

---

## 5. 行上带出的字段（展示，不参与列入）

生成时从节点 **抄一份快照** 落到行上。树仍是分类真相；再生成按当时的树重算。

| 列 | 来源 |
|----|------|
| `weld_info` / `remark` | 节点原文 |
| `has_outsource_remark` | 备注含约定词则为真（提示，不是开关） |
| `material` / `thickness_text` / `material_mill` | 材料列；厂家是钢厂/紧固件商/胶商，**不是**二级冲焊厂 |
| `parent_part_number` / `parent_part_name` | 直接父件（L1 即供货总成；退化供货件为空） |
| `internal_number` | 本行节点内部号（可空；业务上当 ERP 编号）。不是 L0 内部号。列表弱化展示 |
| `l0_part_number` / `l0_part_name` | **核对凭据**：所属供货总成零件号/名称。L1 沿父上溯到 L0；退化供货件、异常 L0 **填自身**。列表、导出必带，不要让人只对着本行零件号对材料清单 |
| `excel_filename` / `excel_row` | **核对凭据**：导入时的 **原始 Excel 文件名**、**Excel 界面行号**（1-based，与打开原件看到的行号一致）。从 `bom_nodes` 抄，列表/导出必带 |
| `excel_sheet_name` | 来源工作表名（节点有则抄）。多表时和行号一起对原件 |
| `child_count` | 直接子节点数 |
| `source_node_id` | `bom_nodes.id`；同一零件号可出现在多棵树上 |
| `data_gap` | 可空。退化供货件材料/料厚/厂家全空 → `l0_material_missing` |
| `alert_code` | 可空。§7.4 告警码，不否决列入 |

约定词（仅打标，可按项目补）：`凸焊总成供货`、`总成供货`、`冲压单件供货`、`单件供货`、`黑漆件供货`、`电泳`。

本文不解析、不猜测二级供应商名称。行上 **禁止** 存单价、一口价。合同对方由采购 **点选** 供应商主数据，见指定供应商设计，**禁止**用 `material_mill` 或年度价厂名顶替，禁止自由填厂名。

---

## 6. T13J 金标准

解析口径与现网 `node_parser` 一致：A 列非数字即停。

| 树上 | 件数 | 采购对象清单 |
|------|------|----------------|
| L0 | 44 | — |
| L0 有子件 | 30 | 其中全部 L1 无内部号的 → `l0_degenerate`；其余不进 `object` |
| L0 无子件 | **14** | 全部 `l0_degenerate` |
| L1 有内部号且有子件 | 以现网为准 | `l1_subassembly` |
| L1 无内部号 | 以现网为准 | 核对区 `other_leaf`（如点焊胶、焊接螺柱组合件）；不进采购对象 |
| L2 | 108 | 不落行 |

`other_leaf` **允许非零**。`l1_stamping` 实数用 §3 跑出来，写入清单头计数。

退化供货件亚类金标准：

| 亚类 | 件数 | 零件号 |
|------|------|--------|
| `special_process` | 6 | `501012176AA`、`554003393AA`、`403014115AA`、`403014116AA`、`T15-3301097`、`T15-3301098` |
| `stamping_blank` | 8 | 含顶横梁Ⅱ `502008112AA` 等 |

焊信一致性（告警，不改分类）：53 个分总成全部有焊接原文；L1 叶子焊接原文为 0。

---

## 7. 检测：怎样才叫清单对了

对 **一个 snapshot** 必须同时满足。7.1–7.3 决定清单头 `qa_passed`。失败仍落库（检测要看见哪漏了）。`qa_passed=false` 时 **仍允许确认、审核、改供应商**（黄条仅展示）；已审行跳过不改。导出仍允许（标明未通过）。

### 7.1 完备

```text
|{无子件或全部 L1 无内部号的 L0}|  == |object_kind=l0_degenerate|
|{l0_degenerate}|  == |special_process| + |stamping_blank|
|{结构化总成下、有内部号且有子件的 L1}|  == |object_kind=l1_subassembly|
|{结构化总成下 L1 叶子}|  == |有内部号的冲压件| + |无内部号叶子（核对区）|
```

第三条、第四条只统计 **所属 L0 不是退化供货件** 的 L1。无内部号的 L1 **不得** 出现在采购对象区。退化供货件名下的 L1 不落行。  
亚类必须盖住全部退化供货件；**冲压毛坯件数可以非零**（T13J=8），不因此否决检测，也不编成电泳。

生成日志成功摘要在采购对象计数下写亚类件数，并加一行中性说明：`冲压毛坯 N 件（可发货；无焊信则不编处理费）`。毛坯发货是正式交件方式。不点名零件，不写成「已按毛坯供货」，不因此否决检测。

### 7.2 互斥

同一 `source_node_id` 只出现在一行。  
至少有一个 L1 带内部号的 L0、全部 L2、无内部号的 L1：`section=object` **零行**。退化供货件（可有无内部号的一级件）**可以**在采购对象区。

### 7.3 结构对账

| 检查 | 合格 |
|------|------|
| `l1_subassembly` 的 `child_count ≥ 1`，孩子全是 L2 | 是 |
| `l1_stamping` 的 `child_count = 0` | 是 |
| `l0_degenerate` 的全部 L1 都没有内部号 | 是（`child_count` 可以为 0） |
| `section=object` 的 L1 必须有内部号 | 是 |
| 每个 `section=object` 的 L1，父节点是带内部号一级件的 L0 | 是 |
| 每一行 `l0_part_number` 非空（退化供货件 / 异常 L0 为自身） | 是 |
| 每一行能从节点抄到 `excel_filename` 与 `excel_row` | 是（抄不到则告警，不挡列入） |

### 7.4 告警（不否决 `qa_passed`）

| `alert_code` | 含义 |
|--------------|------|
| `l0_outsource_remark` | 子件带内部号的 L0 备注含「凸焊总成供货」等；**仍不列入采购对象** |
| `subassembly_no_weld` | `l1_subassembly` 且 `weld_info` 空（T13J 不应有） |
| `stamping_has_weld` | `l1_stamping` 且 `weld_info` 非空（T13J 不应有） |
| `l0_material_missing` | 退化供货件材料/料厚/厂家全空（现网解析常如此） |
| `other_leaf_looks_stamping` | `other_leaf` 名称像支架/加强板且有料厚 |
| `excel_trace_missing` | 节点上原始文件名或行号为空，对原件核对不便 |

修 `node_parser`、让退化供货件落到自身材料，是 **解析** 问题，不是改列入规则。修好后再生成，`l0_material_missing` 应变少。

---

## 8. 表（按业务命名）

这是 **一版材料清单的采购对象台账**，不是临时计算结果。页面和导出只读本切片结果表，**禁止**每次打开列表再扫 `bom_nodes` 当结果。

### 8.1 三张表

```text
bom_procurement_object_lists          清单头：一版 BOM 一份采购对象清单
 └── bom_procurement_objects          清单行：采购对象 / 标准件/胶等 / 异常
bom_procurement_object_generate_logs  一次「开始生成」一条终态日志（同步，无 processing）
```

| 表 | 业务 |
|----|------|
| `bom_procurement_object_lists` | 这份材料清单的采购对象清单一份（含检测结论、结构计数） |
| `bom_procurement_objects` | 清单里的每一行：要采购核对的对象，或核对用的标准件/胶等、异常 |
| `bom_procurement_object_generate_logs` | 生成历史：范围、计数、检测、过程全文 |

归属 **`bom` 切片**。头表 `snapshot_id` 外键 → `bom_snapshots.id`，`ON DELETE CASCADE`。  
无直接下游时覆盖导入会 **删旧 snapshot 再建**，清单随材料清单一起没，必须对新 snapshot **再生成**。该版本已有采购对象清单或焊接工艺拆解时 **禁止** 覆盖导入 / 删除材料清单（须升 BOM 版本，或先删这些直接下游）。一期 **不** 把确认迁到新 snapshot（`source_node_id` 已变，对错行的风险大于省勾选）。

### 8.2 清单头 `bom_procurement_object_lists`

一 snapshot 至多一份清单。唯一键：`snapshot_id`。

| 字段 | 业务含义 |
|------|----------|
| `snapshot_id` | 哪一版材料清单 |
| `location` / `vehicle_model` / `bom_version` | 从 **snapshot 头**冗余（设变后仍是 SOP 字如 `D/09`，不是节点上的 `EC-*`）。列表/批量取件 **不要**拿本字段当 WHERE 主键（§8.5 / 改前必读第 7 条）；界面「项目」= `vehicle_model`。新生成/建空头抄 snapshot；历史允许别名/小写（§13） |
| `source_filename` | 该版材料清单导入时的 **原始 Excel 文件名**（`bom_snapshots.source_filename`），页头核对用 |
| `qa_passed` | 7.1–7.3 全过：这份清单可以给采购用 |
| `qa_error_text` | 未通过时的人读原因；通过可空 |
| 结构计数 | `l0_count`、`l0_with_children_count`、`l2_count`、`subassembly_child_sum` |
| 采购对象计数 | `object_l0_degenerate_count`、`object_l1_subassembly_count`、`object_l1_stamping_count` |
| 核对区计数 | `other_leaf_count`、`anomaly_count` |
| `generated_at` / `generated_by` | 最近一次生成 |

`AuditUserMixin` 照现网其它 BOM 结果表。

### 8.3 清单行 `bom_procurement_objects`

一行 = 树上一个节点在本份清单里的角色。

| 字段 | 业务含义 |
|------|----------|
| `list_id` | 所属采购对象清单，级联删 |
| `section` | `object` 采购对象；`other_leaf` 标准件/胶等（核对）；`anomaly` 异常（核对） |
| `object_kind` | 仅 `section=object`：`l0_degenerate` / `l1_subassembly` / `l1_stamping`；其余空 |
| `degenerate_subtype` | 仅退化供货件：`special_process` / `stamping_blank` |
| `source_node_id` | 生成时的 `bom_nodes.id` |
| `part_number` / `part_name` / `level` / `node_role` | 本行零件快照 |
| `internal_number` | 从该行节点抄内部号（可空；业务上当 ERP 编号）。**不是** L0 内部号。列表弱化展示，方便找不到供应商时去 ERP 联查 |
| `qty` / `qty_unit` | 相对父件；`qty` 用 `Numeric` / `Decimal` |
| `l0_part_number` / `l0_part_name` | **核对凭据**。所属供货总成（材料清单总成列）。L1 / 标准件/胶等：上溯到 `level=0`；退化供货件、异常（有子件的 L0）：填本行。必填，禁止空 |
| `parent_part_number` / `parent_part_name` | 直接父件。L1 与 `l0_*` 相同；退化供货件为空。结构用，**不够当核对列**（退化供货件没有父件） |
| `excel_filename` | **核对凭据**。该行在原件中的文件名，从节点 `excel_filename` 抄（与清单头 `source_filename` 通常相同，行上自带以免导出后对不上） |
| `excel_sheet_name` | 工作表名，节点有则抄 |
| `excel_row` | **核对凭据**。Excel **界面行号**（1-based，与打开原件左侧行号一致），从节点 `excel_row` 抄。不是库内 id、不是 sort_no |
| `child_count` | |
| `weld_info` / `remark` / `has_outsource_remark` | 原文与经营话术提示 |
| `material` / `thickness_text` / `material_mill` | 牌号/料厚/钢厂等，不是二级厂名 |
| `data_gap` / `alert_code` | 可空 |
| `confirm_status` | 仅采购对象：`pending` 待定 / `outsourced` 外发 / `in_house` 自制。核对区行固定 `pending` 且 API 禁止改 |
| `confirmed_by` / `confirmed_at` / `confirm_remark` | 最近一次确认（外发/自制） |
| 审核 | 仅 `section=object`。`audit_status`：`pending` 待审 / `approved` 已审。字段同焊接单价：`audited_by` / `audited_at` / `audit_remark`，`reverse_audited_by` / `reverse_audited_at` / `reverse_audit_remark`。核对区不审核 |

唯一键：`(list_id, source_node_id)`。同一节点不能既是采购对象又是标准件/胶等。

### 8.4 生成（覆盖写）— 只服务 SOP snapshot

**写死：生成页只读 snapshot，因为它是 SOP；后续全部走工程变更。**

入口：选定 **基地 + 项目 + snapshot 头版本**（`bom_snapshots.bom_version`，如 `D/09`）→ `get_by_unique_key` 解析 **唯一** snapshot → 点 **生成**。对齐焊接工艺拆解「从树上生成」，不是上传 Excel。写门禁见 §13。

| 本页做什么 | 本页不做什么 |
|------------|--------------|
| 读 **该 snapshot** 全部 `bom_nodes`，整包分类 + 检测 + 删头重写 | 读节点 `bom_version=EC-*` 当范围；材料清单 Excel 表头版本当生成键 |
| 版本下拉 **只列 `bom_snapshots.bom_version`**（`version_source=snapshot`） | 默认 `/filters/cascade` 的 L0 节点版本字（会露出 `EC-202505`） |
| 无设变、林子仍是投产态时整包生成 / 再生成 | 设变种树后仍点生成「补」新树对象（须走工程变更重传） |

1. 读该 snapshot 全部 `bom_nodes`，纯函数分类 + 检测。  
2. **一个事务**：删该 snapshot 旧清单头（级联删行）→ 写新头 + 新行。  
3. 同一 snapshot 再生成：按 `source_node_id` **带回** 旧行的确认三态 / 确认人时 / 备注。新出现的节点 `pending`；已不在树的确认丢弃。合同对方 `supplier_name` 的带回见 [指定供应商](bom-procurement-object-supplier-design.md)。  
4. 无直接下游时覆盖导入换了 snapshot：旧清单已随旧 snapshot 删掉，新生成全是 `pending`。已有采购对象或焊接拆解则材料清单禁止覆盖。  
5. 写一条 `bom_procurement_object_generate_logs`（成功或失败终态）。

检测未通过：照样提交，`qa_passed=false`。不要为了「名单好看」只写一半采购对象。

**已审核锁定：** 该 snapshot 下只要有一行 `audit_status=approved`，禁止再生成覆盖（`BusinessException` `code=409`）。须先 **批量反审核**。不要把已审行悄悄跳过再抽一半。

**设变门禁：** 该 snapshot 一旦有已失效树根、或树根生效月 ≠ 项目 SOP 开始月 → `snapshot_blocks_full_generate` → 409。缺对象 / 新树对象 **只走** [工程变更](../engineering-change/design-change/part-number-revision-design.md) §4.4 插行，**禁止**在生成页做增量。

一期 BOM 节点量级 **同步生成**（无异步任务、无 processing 锁）。生成页有进度条是前端等待 HTTP，不是后台 worker。

### 8.5 确认、审核、CRUD

对齐现网 **年度零件价 / 焊接单价** 列表：删除、审核、反审核 **只走批量、按范围、意见必填**。禁止单条审核/反审核/删除 API，禁止操作列做这三件事。

**确认（业务勾选，不是审核）**

- 只改 `section=object` 的 `confirm_status`（待定 / 外发 / 自制）和确认备注。
- 不改 `object_kind`、核对凭据、材料快照。
- `qa_passed=false` **不拦**确认；`approved` 时 **跳过不改**（不抛错、不写入）。检测口径见 §14：列表档案不按月裁；核价侧才按账期月问命中树。
- 确认允许 **单条**（操作列改外发/自制）：这是「这一件怎么买」，不是锁定。

**删除 / 审核 / 反审核（只批量，按基地 + 项目）**

body 带 **范围键**，不传行 id、不按勾选。与[协议](../costing/procurement-contract-report-design.md)列表取件同形：**不要**必填 BOM 版本。

| 项 | 口径 |
|----|------|
| 范围 | **基地 + 项目**（该范围内全部清单头 / 行）。**不加年+月**；**不过**「是否已过期」筛。可选 `bom_version`：有值时只裁 **爬到的 L0** 版本字命中的行，**不是**按清单头版本拆范围、也不是 source 本行字 |
| 入口 | 列表工具栏按钮 + 抽屉；**审核意见 / 反审核原因必填**（`min_length=1`） |
| 删除 | 无版本且范围内无 `approved` → 对该基地+项目下 **全部** 清单头 `delete_list`（行级联）；有 `approved` → 只删命中的 `pending`（含标准件/胶等、异常），已审跳过，返回 `skipped_approved_count`。有版本时只删 **爬到的 L0** 版本字命中的 pending，不清无关头 |
| 审核 | 把范围内（经可选 **L0 版本字** 裁行后）`section=object` 且 `pending` 改为 `approved`；已审跳过；意见写入 `audit_remark` |
| 反审核 | 把范围内（经可选 **L0 版本字** 裁行后）`section=object` 且 `approved` 改回 `pending`；非已审跳过；原因写入 `reverse_audit_remark` |
| 锁定 | `approved` 禁止改确认、禁止 SOP 再生成覆盖 |
| 检测 | QA 横幅读该基地+项目下清单头聚合（任一未通过则标明）；**不**拿「墙钟本月命中」当列表默认门禁。核价覆盖检查才按账期月，见 §14 |

不要求先确认外发才能审。列表要能筛未确认已审。

无已审且无版本筛时整单删头，不必重算。有已审时删 pending 后重算清单头计数；完备性被破坏则 `qa_passed=false`。核对区不审核、不反审核。

**CRUD**

| 字母 | 做什么 | 不做什么 |
|------|--------|----------|
| C | **生成** 整份清单 | 手填一行乱入分类 |
| R | 列表分页、summary、单条详情、生成历史 | |
| U | 单条改确认（待审） | 改总成号、Excel 行号、分类；单条审核 |
| D | **仅批量删除**（按范围；无已审清清单头，有已审跳过） | `DELETE /items/{id}`；操作列删除 |

**导出 Excel**

- 与列表同一套筛选，不分页。
- 三张工作表（采购对象 / 标准件及胶等 / 异常），无封面。必含原件文件名、行号、供货总成、本行零件、对象种类、确认、审核。
- 冻结 `I6`；打印标题 `A:H`。相邻行相同供货总成零件号+名称时合并 G/H。
- 色板与冲压模具费导出同族（靛蓝标题 / 石板分组 / 品牌红判定）。
- 零件号后：**短码**（数字末四位，核对焦点，石板色加粗）；再 **内部号**（灰色弱化）。列表仍无「关注点」列。
- `qa_passed=false` **仍允许导出**（标明未通过）。

### 8.6 分层

```text
Router  → ProcurementObjectService 门面（查询 + 委托）
              ├── GenerateService      写门禁 + 分类 + 覆盖写（含 snapshot_blocks_full_generate）
              ├── InsertService        工程变更种树后本树插行（不 commit）
              ├── AuditService         单条确认 / 按范围批量审核·反审核·删除
              ├── GenerateLogService   成功进生成事务；失败 rollback 后单独提交
              ├── ExportService        与列表同一套筛选，不分页
              └── classify / labels / mapping / row_write
                    classify 纯函数；mapping 树根期 → VO + scope_from_query；
                    row_write.build_object_row_write 供 generate / 插行共用（始终 pending 审核）
                    └── 只读 BomNodeRepository / BomSnapshotRepository
```

禁止 Router 写 SQL、调 Parser、调 `LocationService` / `VehicleModelService`。  
禁止生成时读年度价、焊接拆解、冲压价、供应商主数据。  
Parser 不参与（树已在 `bom_nodes`）。

路径：

```text
app/models/bom/procurement_object.py
app/models/bom/procurement_object_generate_log.py
app/repositories/bom/procurement_object_repository.py
app/repositories/bom/procurement_object/   queries · writes · types（ScopeFilters / HUD TypedDict）
app/services/bom/procurement_object/   service · generate/service · insert/service · audit/service · generate/log · export/service · classify · labels · mapping · row_write
app/routers/bom/procurement_object.py
app/schemas/dto|vo/bom_procurement_object_*.py
static/js/features/bom/procurement-object/
```

对人展示文案（勿在页面/导出再写一套）：

- `app/services/bom/procurement_object/labels.py`
- `static/js/features/bom/procurement-object/labels.js`

API 前缀：`/api/bom/procurement-objects`。

| 入口 | 范围键 |
|------|--------|
| **生成** / prep-stats | **基地 + 项目 + snapshot 头版本**（只找 `bom_snapshots`；不是客户端传 `snapshot_id`；不是 L0/`EC-*`） |
| **列表 / 导出 / summary / 批量** | **基地 + 项目** 必填；`bom_version` **可选**（只筛爬到的 L0 版本字）。**禁止**用版本解析清单头 / snapshot |
| **供应商批传** | 与生成页同钥：基地+项目+snapshot 头 → `get_by_unique_key` → `get_list_by_snapshot_id`。**禁止** EC / 全部版本 / L0 浏览 |

列表 / 导出 **不加** `year` + `month`；过期筛用 `include_expired`（§14）。批量审核 / 反审核 / 删除 **不传** `include_expired`。取件：`list_objects_by_location_vehicle`；**每行必须爬到 L0**；有版本则按 **L0.bom_version** 裁。无任一清单头 →「请先生成」；有头但筛空 → 空表。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/generate/prep-stats` | 生成页 KPI；Query 含 snapshot 头版本 |
| POST | `/generate` | body：基地+项目+**snapshot 头版本**；只读该 snapshot。有已审 → 409；非 SOP 林（`snapshot_blocks_full_generate`）→ 409。设变增量不走本接口 |
| GET | `/generate/logs` | 生成历史分页 `page`+`size` |
| GET | `/generate/logs/{log_id}` | 过程全文 |
| GET | `/summary` | Query：基地+项目（版本可选，不影响头聚合）。该基地+项目下清单头：`qa_passed` = 全部通过才 true；未通过文案拼接。列表 QA 横幅用。**不是** HUD 计数源 |
| GET | `/` | 分页 `page`+`size`；必填感由前端：基地+项目；`bom_version` 可选=**爬到的 L0** 版本字浏览；另筛 section / object_kind / confirm_status / audit_status / part_number / l0_part_number / excel_row / `has_supplier`；`section` 空 = 全部。`include_expired` 默认 `true`（§14）；**不要** `year` / `month`。响应 `filters.summary` = HUD |
| GET | `/items/{id}` | 单条详情（VO 带所属树根四列） |
| PATCH | `/items/{id}/confirm` | 单条确认三态（待审） |
| POST | `/batch-approve` | **按基地+项目** 批量审核；可选版本裁行；`audit_remark` 必填；禁止 ids；不过期筛 |
| POST | `/batch-reverse-audit` | **按基地+项目** 批量反审核；可选版本裁行；`reverse_audit_remark` 必填；禁止 ids；不过期筛 |
| POST | `/batch-delete` | **按基地+项目**：无版本且无已审 → 清该范围全部清单头；有已审 / 有版本 → 只删命中 pending；禁止 ids；不过期筛 |
| GET | `/export` | 与列表相同筛选（含可选版本、`include_expired`），不分页，Excel。**不是**协议签字件，**不要**套「导出必须全部版本」400 |

禁止：`POST /items/{id}/approve`、`POST /items/{id}/reverse-audit`、`DELETE /items/{id}`、按勾选 id 的 batch。

---

## 9. 产品：生成 / 列表 / 审核 / 导出

侧栏（焊接工程下）：**采购对象** — **两个界面**：生成页 + 列表页。

### 9.1 前端风格

两页视觉与交互壳对齐 `static/js/features/costing/stamping-part-cost/`，不要对齐年度零件价的浅阶面板，也不要自创第三套。

| 页 | 对照 | 抄什么 |
|----|------|--------|
| 生成 | `stamping-part-cost/calc/template.js` | 顶栏标题；筛选条；筛选下 KPI；主按钮「开始生成」；进度面板 |
| 列表 | `stamping-part-cost/list/template.js` | HUD 外框；看板 + 批量按钮；胶囊筛选；密表；`page-size.js`；抽屉 z-index ≥ 80/85 |

强调色页内统一 **`#FF1E27`**，不要和 `#d32f2f` 混用。  
HUD：**采购对象**是霓虹强调格；标准件/胶等、待审、已审为普通计数。检测未通过用警告文案，**不要**照抄「本期均价」。  
操作列只 **确认**（及详情）；禁止整行点击；**无勾选列**。批量审核/反审核/删除的规则仍是 §8.5。

禁止另起 `style.css` 业务 class。生成页 KPI 下可有一行 9px 灰色说明（退化供货件口径），禁止卡片、黄条、加粗抢主按钮。

### 9.2 页面内容

**生成页（SOP only）**

- 必选：基地 / 项目 / **snapshot 头版本**（只列 `bom_snapshots.bom_version`，如 `D/09`）。  
- 级联走 BOM 上级域：`GET /api/bom/filters/cascade?version_source=snapshot`（前端 `snapshot-cascade.js`）。**禁止**默认 L0 cascade（会露出 `EC-*`）；**禁止**在采购对象域另挂 options / cascade 路由。  
- 文案写死：本页只生成 **投产材料清单（SOP）** 整包；设变后请走 **工程变更**，不要在本页补生成。  
- 种树后门禁 409 时 Toast 指向工程变更，不要暗示「换个 EC 版本再点生成」。

**列表页**

列表页签：**全部**（默认，不传 `section`）| 采购对象 | 标准件/胶等 | 异常。HUD 展示采购对象条数、标准件/胶等、待审、已审 = 列表响应 `filters.summary`（跟当前「是否已过期」等筛，默认含已过期），**不是**本月账，也 **不是** `GET /summary`。不要用清单头整包 `qa_passed` 当 HUD 成功态；检测未通过用 QA 横幅（读 `/summary`：该基地+项目下任一清单未通过则标明）。

筛选条：必选 **基地 / 项目**；**版本**默认 **全部版本**（空）；另有对象种类 / 确认 / 审核 / 零件号，以及：

| 筛 | 文案 | 默认 |
|----|------|------|
| `bom_version` | **版本**（全部版本 / 树根版本字） | **空 = 全部版本**。有值只筛 **爬到的 L0** `bom_version`，**不是**清单头键、不是 source 本行。对照：芜湖 T13J + `EC-202505` → 出设变新树行；选全部 → 档案全貌含 SOP+设变 |
| `include_expired` | **是否已过期**（全部 / 不含已过期） | **包含已过期**（全部） |
| `has_supplier` | **是否指定供应商**（已指定 / 未指定） | 空 = 全部 |
| 供应商文本 | **供应商**（缩写 / 工商名称 / ERP） | 空 |

禁止再写过滤标签「对方」。禁止摆年、月下拉当列表 as_of。禁止把 cascade 的 `EC-*` 当成「尚未生成」的清单头键。

列表须有 **生失效一列区间**（与产品结构 / 模具清单同一套 `fmtPeriodRange`，如 `2025年07月 – 2026年12月`），值 **只认所属 L0 树根** 四列，与结构树 L0 同值；对象行不能改。禁止读 source 节点自身四列当展示真相（库里虽与树根同值，本切片仍只认树根）。没有这一列，包含已过期也分不清哪行是历史。

工具栏：**批量审核 / 批量反审核 / 批量删除** + 导出 Excel。抽屉展示当前范围（基地 · 项目 · 版本或「全部版本」），意见必填。删除口径见 §8.5 / §14。禁止勾选行再批量。

**核对列：** 列表与导出须能直接对回原件：

1. **原件**：`excel_filename`（页头再用清单的 `source_filename`）
2. **行号**：`excel_row`（Excel 界面 1-based）
3. **供货总成**：`l0_part_number` / `l0_part_name`
4. **本行**：零件号 / **短码**（数字末四位）/ 内部号（弱化）/ 名称
5. **对象种类 / 确认 / 供应商 / 审核**
6. **生失效**（所属 L0 树根区间，只读；只认树根）

列表 **无「关注点」列**。不要让采购只拿本行零件号去材料清单里搜。工作表名有则一并展示。

导出与 §8.5 相同。同一 `part_number` 多行都导出。不提供「Excel 勾完再导回确认/审核」；确认和审核只在系统里做。

权限（已进 `catalog.json`）：

| 码 | 用途 |
|----|------|
| `menu:bom-procurement-object-group` | 侧栏分组 |
| `menu:bom-procurement-object` | 生成页 |
| `op:bom-procurement-object:generate` | 生成 |
| `menu:bom-procurement-object-list` | 列表页 |
| `op:bom-procurement-object-list:view` | 查询 |
| `op:bom-procurement-object-list:update` | 单条确认 |
| `op:bom-procurement-object-list:delete` | 批量删除 |
| `op:bom-procurement-object-list:approve` | 批量审核 |
| `op:bom-procurement-object-list:reverse` | 批量反审核 |
| `op:bom-procurement-object-list:export` | 导出 Excel |

---

## 10. 和现网 BOM 的边界

| 模块 | 关系 |
|------|------|
| `bom_nodes` | 分类时只读；对外以采购对象清单为准 |
| 覆盖导入 | 有采购对象或焊接拆解则禁止；无直接下游才删 snapshot 并级联删清单 |
| `node_parser` | 生成不改解析；材料落不到退化供货件时打 `data_gap` |
| `manufacturing_category` | L1 叶子是否冲压件，复用，不新开词典 |
| 焊接工艺拆解 | **不读** |
| 年度零件价 | **不读** |
| 基地 | 生成 `require_enabled`；列表筛 `list_registered` + 查询 `expand_for_query`。本表不加基地外键 |
| 项目 | 列表筛 `list_registered`。生成不 `require_introducible`。本表不加项目外键 |
| 供应商 | 生成不读、不猜。行上指定对方见独立设计 |

---

## 11. 做 / 不做

| 做 | 不做 |
|----|------|
| 按树列入三类采购对象并落库 | 用备注 / 焊信 / 年度价决定列不列入 |
| 清单头记检测结果；失败也落库 | `qa_passed=false` 仍当「名单已合格」 |
| 标准件/胶等 + 异常进核对区 | 把子件带内部号的供货总成、L2 写入采购对象 |
| 同 snapshot 再生成带回确认；已审禁止覆盖；**生成页只读 SOP snapshot** | 覆盖导入后自动把确认对到新 `source_node_id`；设变后仍走生成页整表重写 / 补 EC 树；对象行另写生失效；用 source 节点自身四列当对象时段；清单头整包数当本月账；列表默认按墙钟月裁掉历史 |
| 列表/批量取件 = 基地+项目；版本可选=**爬到的 L0** 字；必须爬到树根 | 用 `get_list_by_scope(基地,项目,EC-*)` 找头；用 source 本行版本字 / 生失效绕过爬树 |
| 确认外发/自制（单条）；批量审核/反审核/删除（按基地+项目，不加年+月） | 单条审核、单条删除、按 id 勾选批量；手建一行改分类；Excel 导回当审核 |
| 生成页/列表页抄零件价格计算 + 一览 | 抄年度零件价列表壳；自创第三套样式 |
| 已审禁止改确认/删除/再生成 | 算单价、应成本 |
| 退化供货件全部列入，再标亚类 | 无工艺就不列入，或编成电泳 |
| 同一零件号多行都保留 | 按零件号去重 |
| 对人展示走 `labels` | 页面再写「其它叶子」「退化 L0」当产品文案 |
| 生成前过基地 `require_enabled`；列表基地筛主数据 | 本切片代建基地/项目；给清单头加基地/项目外键 |
| 界面写「项目」 | 再写「车型」当产品文案 |

---

## 12. 相关代码与文档（本切片）

| 位置 | 角色 |
|------|------|
| `app/models/bom/node.py` | `level` / `parent_id` / `node_role` / `weld_info` / `remark` / `excel_row` |
| `app/parsers/bom/node_parser.py` | 树怎么进库；L0 材料是否落地 |
| `app/common/bom/manufacturing_category.py` | L1 叶子是否 `stamping` |
| [welding-process-breakdown-design.md](welding-process-breakdown-design.md) | 拆解；生成清单时不读 |
| `app/services/bom/bom/upload/` | 再导按树对齐，不删 snapshot。真删头仍走 `assert_bom_scope_unused`。落库前拦一物一码 |
| [bom-annual-part-prices-design.md](bom-annual-part-prices-design.md) | 价表；本文不读 |
| [location-design.md](../masterdata/location-design.md) | 基地；生成写门禁、列表筛 |
| [vehicle-model-design.md](../masterdata/vehicle-model-design.md) | 项目；列表筛；本文不是下一跳 |
| [supplier-design.md](../masterdata/supplier-design.md) | 合同对方主数据；生成不读 |
| [bom-procurement-object-supplier-design.md](bom-procurement-object-supplier-design.md) | 行上指定合同对方（已落地；可空 FK → 供应商） |
| [bom-procurement-object-supplier-upload-design.md](bom-procurement-object-supplier-upload-design.md) | 按清单范围 Excel 批改对方（已落地） |
| [assembly-costing-design.md](../costing/assembly-costing-design.md) | 下游应成本；集合以本清单为准 |
| [procurement-contract-report-design.md](../costing/procurement-contract-report-design.md) | 签约横表（已落地）；只读本清单 + 应成本 |
| [bom-process-die-effective-period-design.md](../engineering-change/design-change/bom-process-die-effective-period-design.md) | 树根生失效；本清单有效期 **只认 L0 树根**；列表 join 展示、过期筛相对墙钟；核价仍按账期月 |
| [part-number-revision-design.md](../engineering-change/design-change/part-number-revision-design.md) | 设变增量带出（§14） |
| `static/js/features/costing/stamping-part-cost/calc/` | 生成页 UI 对照 |
| `static/js/features/costing/stamping-part-cost/list/` | 列表页 UI 对照 |

---

## 13. 基地 / 项目（主数据）

分类规则不改。本节只补 **写谁、筛谁、外键挂谁**。细则不在本文重写，调上游设计。

引用保护（宪法 §4.3）：**子声明、父不知；只拦直接下游。** 项目的下一跳是 `bom_snapshots`，不是本清单。清单头只声明 `snapshot_id → bom_snapshots.id`（`ON DELETE CASCADE`，同切片附属结果）。生成日志、清单行上的 `location` / `vehicle_model` 字符串副本 **不加** 基地外键、**不加** 项目外键。项目 Model 禁止 `relationship` 指向本表。

### 13.1 已定规则

| # | 规则 |
|---|------|
| O1 | 没有已启用基地，不能新生成。`LocationService.require_enabled`。找不到 / 已禁用 → 去 `#/location`，不代建 |
| O2 | 生成不是传 BOM。BOM 上传只要求项目已登记（含已结束），不看本月是否可引入。本文 **禁止** 再套一套 `require_introducible`。已失效项目：已有 snapshot 仍可生成 / 再生成；没有 snapshot 不能生成 |
| O3 | 不立项。代号对不上已有 snapshot → 「未找到对应材料清单」，去焊接工程上传，不去项目一览表代建 |
| O4 | 库字段仍 `vehicle_model`。界面、Toast、抽屉、导出页头写 **项目**，不要写车型 |
| O5 | 代号查找前 `normalize_vehicle_model`（含大写）。`t13j` 与 `T13J` 同一代号。不做项目别名展开（项目设计 P14） |
| O6 | 清单头 `location` / `vehicle_model` / `bom_version` **抄 snapshot 头**（设变后仍是 SOP 字）。不在生成时改写 snapshot，也不为迁就外键改历史清单头。列表取件 **不要**用头上 `bom_version` 当 WHERE |
| O7 | 列表：基地选项 `list_registered`；选了基地后查询条件 `expand_for_query`。项目选项 `VehicleModelService.list_filter_codes`。**禁止**本表 `DISTINCT location` / `DISTINCT vehicle_model` 当身份选项。**版本下拉 = 「全部版本」+ 该基地+项目下 L0 树根版本字（浏览筛）**；默认空；有值时 **先爬到 L0 再比 `L0.bom_version`**。HUD 计数来自列表 `filters.summary`。导出按请求 `location` 精确匹配（不走 expand） |
| O8 | **生成页只读 snapshot（SOP）。** 下拉 = `snapshot-cascade.js` → `GET /api/bom/filters/cascade?version_source=snapshot`（BOM 上级域）。**禁止**默认 L0/`EC-*`；**禁止**采购对象域自挂 cascade。列表页版本字 = 树根浏览筛（须爬到树根，默认 L0 cascade），与生成页分源。设变后整包 generate 409，后续只走工程变更。废止写死四基地 |
| O9 | 确认 / 审核 / 反审核 / 删除是改已有清单，不过 `require_enabled`。基地禁用后已有清单仍可查、仍可反审核以便清理。新生成仍走 O1 |

### 13.2 生成：怎么找到 snapshot（只认 SOP 头）

干净库约定：`bom_snapshots.location` / `vehicle_model` 落库时已是规范名 + 归一化代号（与 BOM 上传同一套）。生成 **不** 为历史「青岛基地」等别名再 expand。

**本入口只服务投产 snapshot。** 版本参数必须是头上的 SOP 字；找到头之后只读该 snapshot 子树。设变写入的节点可以挂在同一 snapshot 下，但 **整包 generate 已被门禁挡住**——不要用本入口按 `EC-*`「再生成一遍」。

1. `canonical = LocationService.require_enabled(raw_location)` → 规范名。不过则硬停。  
2. `code = normalize_vehicle_model(raw_vehicle_model)`。空 / 占位符 → `BusinessException("项目代号无效")`。  
3. `snapshot_scope.require_snapshot(canonical, code, bom_version.strip())`（内部 `get_by_unique_key`），此处 `bom_version` = **snapshot 头版本**（如 `D/09`）。没有 → `NotFoundException("未找到对应材料清单")`。传入节点字 `EC-*` 且头上无此键 → 同样找不到（生成页不得把 L0 cascade 节点字当生成键）。  
4. 若 `snapshot_blocks_full_generate` → 409，文案指向工程变更。  
5. 清单头抄 **该 snapshot** 的 `location` / `vehicle_model` / `bom_version` / `source_filename`。  
6. 其余覆盖写、带回确认、已审 409：§8.4。设变增量 **永不** 走本入口，见 §14.2。

prep-stats 是读：不强制 `require_enabled`（禁用基地仍可看「将列入」）；项目仍 `normalize`。文案「请选定基地 / 项目 / 版本」（生成页版本 = **snapshot 头 / SOP**）。

失败日志：业务事务 `rollback` 之后 **单独提交** 一条 `failed`（现网 `persist_failed`）。成功日志进同一生成事务。

### 13.3 读

查询按库里的字符串。用户选规范名「青岛」时，条件展开为规范名 + 别名，才能命中历史清单头 `青岛基地`。项目筛双方先 `normalize`；对不上历史小写代号，接受（不写第二套查询）。

筛了一个还没生成的项目 → 空表，不是丢数据。选了 **L0 版本字** 但无命中行 → 空表，不要报「尚未生成」（有头才报尚未生成）。

### 13.4 外键（只此一张）

| 表 | FK | 说明 |
|----|----|------|
| `bom_procurement_object_lists.snapshot_id` | → `bom_snapshots.id` `ON DELETE CASCADE` | 同切片附属结果；删 snapshot 清单没 |
| 清单行 `list_id` | → 清单头 `CASCADE` | 附属行 |
| 生成日志 | **无** 指向 snapshot / 项目 / 基地 | 与计算日志同类，间接副本 |

禁止：清单头再声明基地 FK、项目复合 FK。拦「项目还能不能删」的是 `bom_snapshots`，不是本表。

---

## 14. 跟树根有效期（列表 / 设变插行 / 生成门禁已落地）

**写死：本切片有效期只认所属 L0 树根四列。**

| 认 | 不认 |
|----|------|
| 该对象行所属供货总成（`l0_part_number` 那棵树）的 **L0** `effective_*` / `expiry_*` | 对象行自己的列（**没有**；禁止加） |
| | `source_node_id` 指向的 L1/L2 **自身**四列（库里虽与树根同值，本切片仍上溯到 L0 再读；禁止当独立切点） |
| | 项目主数据起止、清单头、墙钟、snapshot 头版本字 |

对象行 **不加** 生失效四列。列表 / 导出 / 「是否已过期」筛 / 核价侧按月命中：一律先定位所属 L0，再读树根四列。SOP 生成与工程变更插行 **不用多抄**；结构页 **只许** PATCH L0 改期（级联子树），对象立刻跟。禁止对象页改期。与焊接拆解同一纪律（拆解也 join 取期、不抄四列；本清单取期锚点是树根，不是任意 source 节点）。

现网实现要点：列表 / 详情 / 确认回写 VO 经 `mapping.rows_to_vos` / `row_to_vo`，树根四列来自 `map_l0_periods`（`(snapshot_id, l0_part_number)` → L0）。列表 / 导出 / HUD 共用 `ProcurementObjectScopeFilters`（工厂 `object_scope_filters`；列表与导出经 `mapping.scope_from_query` 从 Query 组 scope——列表 `locations`=expand，导出 `location`=精确）。查询侧 `_apply_object_filters(scope)` 一条路径。`include_expired=false` 时 `as_of_when_excluding_expired` → 墙钟本月，join L0 + `period_hit_clause`。导出同筛，Excel「生失效」列走同一棵树根 map。

分类规则、一 snapshot 一份清单、`(list_id, source_node_id)` 唯一键：**不改**。作业入口见 [工程变更](../engineering-change/design-change/part-number-revision-design.md) §4.4；树根改造见 [有效期](../engineering-change/design-change/bom-process-die-effective-period-design.md)。

### 14.1 列表是档案，不是月账

采购对象列表要回答「哪些行曾经是、现在仍是采购对象」，不是「这个月车上装什么」。结构树 / 核价才按年+月命中。

| 入口 | 规则 |
|------|------|
| 列表 / HUD / 导出 | **不传年+月 as_of**。筛的是 **是否已过期**，不是「某年某月命中」。取件 = 基地+项目；**每行爬到 L0**；版本可选=树根版本字浏览 |
| `include_expired` 默认 | **`true` = 包含已过期**（有效 + 已到期都出；档案全貌） |
| `include_expired=false` | **不含已过期** = 相对 **墙钟本月**，**所属 L0 树根**仍命中（`is_in_period(now)`）；未到生效月的也不出 |
| 生失效列 | 一列区间 `fmtPeriodRange`，**只读所属 L0 树根**四列。同一零件号新旧两行靠这一列分开 |
| 批量审核 / 反审核 / 删除 | 范围 = **基地 + 项目**；可选版本只裁行；**不加年+月**，**不过期筛** |
| 核价覆盖 / 签约报表 / 引擎发现 | **必须**按账期月命中 **树根**。列表全貌 ≠ 本月账。禁止把 AA/AB 并进本月核价 |

「已过期」相对墙钟本月：**树根**失效月早于本月。不是「选一个历史月再问当时在不在」，也不是问 source 节点自己的失效。界面文案写「是否已过期」，不要叫 as_of，不要摆年+月下拉。

VO 出参带 `effective_year` / `effective_month` / `expiry_year` / `expiry_month`，语义 = **所属树根**，不是对象表列。前端禁止当可编辑；已关闭时段用共用 `hasClosedPeriod` 标红。

HUD 把 AA/AB 并排计数是档案全貌，不要写成「本月待审」。计数来自列表响应 `filters.summary`（跟当前筛）。清单头 `l0_count` / `qa_passed` 仍是 SOP 生成时的整包痕迹；`GET /summary` 只给 QA 横幅读头，**不当** HUD。

筛文案：`has_supplier` 对人写 **是否指定供应商**（已指定 / 未指定）；列与文本筛写 **供应商**。禁止过滤条写「对方」。

### 14.2 SOP 生成 vs 设变插行

**分工写死：生成页 = 只读 snapshot（SOP）整包；后续全部走工程变更。**

| | SOP / 投产 | 工程变更种新树 |
|--|----------------|----------------|
| 谁触发 | 生成页「开始生成」——**只认 snapshot 头** | 设变导入同一事务，只扫新种的那一棵 |
| 读什么 | **仅** `bom_snapshots` + 该头下节点 | 种树给出的新旧对照 + 新树节点 |
| 写 | §8.4 删头重写；按 `source_node_id` 带回确认与供应商 | **不删头、不碰旧行**；`InsertService.insert_for_new_tree` 插新行 |
| 生失效 | **不写对象行**；只认树上 **L0 树根**四列 | **不写对象行**；新树根生效=变更月、失效=项目结束月 |
| 已审 | 有一行已审 → 409 | 不挡；旧已审行不动 |
| 日志 | `bom_procurement_object_generate_logs` | 不写冒充整单覆盖的生成日志；件数记在变更单 |

「开始生成」按 §8.4 整 snapshot 删头重写。该 snapshot 一旦有已失效树根、或树根生效月不是项目 SOP 开始月 → `snapshot_blocks_full_generate` → 409（即使没有已审）。**禁止**在生成页选 `EC-*`、禁止「只补该月」。缺对象 → 工程变更重传。种树与插行同一事务，不走本页 `generate`。SOP 纠错改期请在种树前做；种树后改期走结构页 L0。见 [工程变更 §4.6](../engineering-change/design-change/part-number-revision-design.md)。

### 14.3 从被替换旧树抄确认

只匹配 **被替换的那一棵旧树**（本例 3086AA），禁止扫 snapshot 里其它总成的同号。新行的展示时段跟 **新树 L0 树根**（只认树根），不继承旧树根时段，也不抄四列到对象行。

确认 / 厂家配对 **按现网**（与工程变更 §4.4 一致）：

1. 先同 `part_number` + `section` + `object_kind`  
2. 对不上再按新旧树 **同一位置**（同级兄弟 `sort_no`）抄旧行  
3. **不按**字母版本同茎配对，也不另走变更单号对

| 新树节点 | 落行 |
|----------|------|
| 采购对象，旧树对上（同号或同一 `sort_no` 位置），且 `object_kind` 不变 | 插新行。抄确认三态 / 确认人时 / 确认备注 / `supplier_name`。**不抄** `audit_status`（新行待审）。`l0_*`、父件、Excel 行号、材料快照抄 **新节点** |
| 采购对象，对不上（增加零件；`object_kind` 变了） | 插新行，`pending`，供应商空。禁止从钢厂列 / 备注 / 年度价猜 |
| 该 snapshot 尚无清单头 | 工程变更 **整单拒收**（prep 先问，含完成停止）。`insert_for_new_tree` 无头仍硬停，不代建空头。见工程变更 §4.4 |
| `other_leaf` / `anomaly` | 插新行；无确认可抄 |
| `object_kind` 变了 | 当新号，不抄确认 |

抄来的 `supplier_name` 不跑 `require_enabled`（与 §8.4 带回相同）；全称已不在 `suppliers` 则该行落空，不让整单 `IntegrityError`。插完 **不** 把清单头改成全林计数。

同一零件号可同时有旧树行与新树行。指定供应商批传仍按现网整清单、按零件号去重——同号多行时 **拒绝批传**，改走行上点选。细则仍在供应商上传设计。

### 14.4 删除

按 **基地 + 项目**（可选：**爬到的 L0** 版本字裁行），**不加年+月**，**不过期筛**。无版本且无已审 → 对该范围全部清单头 `delete_list`（§8.5）。有已审 → 只删命中 `pending`（含核对区）；已审跳过；**不清清单头**。有版本筛时只删 L0 版本字命中的 pending。设变之后不要用「只删本月命中」当日常——列表本来就不按月裁；批量也不跟列表过期筛。**禁止**用 `EC-*` 当清单头键去「尚未生成」。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-31 | 初稿：三类对象、检测、导出。 |
| 2026-08-31 | 收成上游文档：只认 BOM 结构与确认。 |
| 2026-08-31 | 落库：清单头/行、生成覆盖、同 snapshot 带回确认。 |
| 2026-08-31 | 文案与表名改为采购对象清单；动作称生成，不再用抽取当业务名。 |
| 2026-08-31 | 行上增加供货总成 `l0_part_number` / `l0_part_name` 作核对凭据；列表筛选与导出必带。 |
| 2026-08-31 | 核对凭据补原始 Excel 文件名与界面行号（清单头 `source_filename`，行上 `excel_filename` / `excel_row`）。 |
| 2026-08-31 | 列表对齐现网：确认、审核/反审核、批量、导出 Excel、按树生成的 CRUD；已审锁定。 |
| 2026-08-31 | 删除/审核/反审核改为只批量、按 snapshot 范围、意见必填；禁止单条与按 id。 |
| 2026-08-31 | 生成页/列表页前端必须对齐 `stamping-part-cost` 计算页与一览（HUD / 筛选条 / 密表）。 |
| 2026-08-31 | 改为已落地：对人展示与内部码分开；补生成日志 / prep-stats；导出三表与列表页签、HUD 与现网一致。 |
| 2026-09-02 | 手填合同对方与签约报表拆出独立设计；本文仍禁止生成时猜供应商、禁止存单价。 |
| 2026-09-08 | 补基地/项目主数据：生成 `require_enabled`、不套 `require_introducible`、清单不是项目下一跳；列表筛主数据；界面「项目」。指定对方改点选供应商主数据（见独立设计）。 |
| 2026-09-08 | 清单行抄节点 `internal_number`；列表弱化展示，供找不到供应商时 ERP 联查。 |
| 2026-09-08 | 导出零件号后加短码（数字末四位，核对焦点）与内部号（灰色弱化）；冻结 `I6`，合并供货总成 G/H。 |
| 2026-09-09 | 一物一码在材料清单上传拦（有内部号的零件号↔内部号一一对应）；本切片生成不再复检。 |
| 2026-09-16 | 批量删除覆盖核对区（标准件/胶等、异常）；审核 / 反审核仍只针对采购对象。 |
| 2026-09-16 | 无已审时批量删除连清单头 `delete_list`（与生成覆盖一致）；有已审仍只删 pending 并重算头。 |
| 2026-09-16 | §14：采购对象严格跟树根有效期；**（已废止）**检测/计数/审核只对该月命中树 → 见 09-18 列表档案口径；列表展示树根生失效；设变只给新树插行。 |
| 2026-09-16 | 设变插行与工程变更同一事务，不走 `generate`；种树后生成页保持拒绝。 |
| 2026-09-17 | 收口：生成页拒绝整包是 **工程变更写入后** 才改的现网门禁；写入前仍按 §8.4 整 snapshot 覆盖。 |
| 2026-09-17 | §14.3：**（已废止）**改图字母版本换号从旧号抄确认 → 见 09-18 改为同号或 `sort_no` 位置。 |
| 2026-09-20 | §14.3：无清单头时工程变更整单拒收，不代建空头。 |
| 2026-09-17 | §14.3：**（已废止）**字母版本同茎含分总成 `-1` → 见 09-18。 |
| 2026-09-18 | §14 拍板选 A：对象行仍不落四列，列表 join 树根展示生失效一列；生成/设变不抄；改期自动跟；与拆解同一纪律。列表不按年+月裁；筛「是否已过期」默认包含；`has_supplier` 文案「是否指定供应商」（禁止「对方」）。核价/签约/引擎仍按账期月命中。批量不加年+月。 |
| 2026-09-18 | §14 写死：有效期 **只认所属 L0 树根**四列；禁止认 source 节点自身四列、项目期、清单头；VO 出参时段语义=树根。 |
| 2026-09-18 | **与现网对齐：** 设变插行 / `snapshot_blocks_full_generate` 已落地；§14.3 抄确认改为同号或 `sort_no` 位置（否决字母版本同茎）；批量审核·反审核·删除不过期筛；HUD 来自列表 `filters.summary`，`GET /summary` 只供 QA 横幅；分层补 `InsertService` / `mapping` 树根期。 |
| 2026-09-18 | 列表/导出/HUD 筛参收成 `ProcurementObjectScopeFilters`；`mapping.scope_from_query`；查询 `_apply_object_filters(scope)`。包内 README 与 §14 现网要点同步。 |
| 2026-09-18 | 可维护性护栏：VO 四列 Field 标明「树根非本表列」；变更记录废止旧「按月裁 / 字母同茎」表述；服务包入口指向 §14；回归测「L1 期≠L0 仍读树根」与「插行配对按 sort_no 不按字母同茎」。 |
| 2026-09-18 | 抽出 `row_write.build_object_row_write`（generate/插行共用，禁止再调私有 `_row_write`）；补插行端到端（抄确认不抄审核）、`has_supplier`、列表 expand vs 导出精确、批量不过期筛回归测。 |
| 2026-09-18 | 可维护性收口：`collect_subtree` 公开；`bulk_create_objects` 返回 id；插行一次 confirm map；mapping `_ObjectVoOverlay`；文首「改前必读」五条不变量。 |
| 2026-09-18 | §13 按干净库收口：生成找 snapshot = `require_enabled` + `normalize_vehicle_model` + 精确匹配；**不做**别名 expand（列表读路径仍 expand）。 |
| 2026-09-19 | 检测未通过不拦确认/审核/改供应商；已审行跳过不改。 |
| 2026-09-19 | **「版本」三义词典**写进文首（snapshot 头 / 树根字 / 清单头冗余）；与协议同词典，消歧四年后误读。 |
| 2026-09-19 | **生成页写死只读 snapshot（SOP）；后续全部走工程变更。** 版本下拉只列 snapshot 头；禁止 EC cascade / 生成页补树。§8.4 / §9.2 / §13.2 / §14.2 / O8。 |
| 2026-09-19 | **列表/批量取件对齐协议：** 范围=基地+项目；**必须爬到树根**；`bom_version` 可选=**L0** 版本字浏览筛；禁止用版本找清单头/snapshot、禁止用 source 本行字/期。summary 聚合该基地+项目下头。**代码已落地。** |
| 2026-09-19 | **供应商批传简化：** 与生成页同钥 + 共用 `snapshot-cascade.js`；禁止第二套级联。改前必读第 8 条。 |
| 2026-09-19 | **级联收回 BOM 域：** 生成/批传 → `GET /api/bom/filters/cascade?version_source=snapshot`；删 PO 自挂 cascade；coverage 收进 `snapshot_scope`；废止 `get_filter_options` 空 stub。§9.2 / O8。 |
| 2026-09-18 | §13 可维护性：文首不变量第 6 条；prep/generate 共用 `_lookup_snapshot`；回归测 normalize 与空代号拒绝。 |
| 2026-10-02 | O2：材料清单上传改为项目已登记即可（含已结束），不再用墙钟月 `require_introducible`。生成仍不套这道门禁。 |
