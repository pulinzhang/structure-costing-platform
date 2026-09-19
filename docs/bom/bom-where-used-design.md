# 零件用在哪 — 设计说明

> **状态：已落地。** 口径以本文与代码为准。  
> 切片：**`bom`**。只读现网 `bom_snapshots` / `bom_nodes`。  
> 对人展示（菜单 / 页标题 / 面包屑）：**零件用在哪**。内部：`where_used`。侧栏禁止写「反查」「内爆」「where-used」。  
> 和 **产品结构** 成对：那边从总成往下看，这边输入零件号看用在哪些总成、哪些项目。  
> 工程变更影响分析可引用本页，切点作业见 [part-number-revision-design.md](../engineering-change/part-number-revision-design.md)。BOM 按月 as_of 见 [bom-process-die-effective-period-design.md](../engineering-change/bom-process-die-effective-period-design.md)，**第一期不接**。  
> 硬约束：分层见 [architecture.md](../architecture.md)；权限流程见 [permission-design.md](../permission-design.md)。

---

## 0. 一句话

输入零件号、4 位短码或名称（模糊），在现网全部材料清单里找出每一次挂载，沿 `parent_id` 追到 L0 供货总成；同时给出「这个件用在哪些供货总成上」的汇总。用量只在同一份清单、同一棵树内连乘，禁止把不同基地或不同项目加总成一个单车用量。

| 对人说法 | 内部 |
|----------|------|
| 零件用在哪 | `where_used`（菜单、页标题、`pageMeta.title`、授权树菜单名同一句） |
| 产品结构 | 现网 `#/bom-structure` 树 |
| 命中 | 一条 `bom_nodes` 记录（同零件号可多处） |
| 路径 | 命中节点沿父走到 L0 的节点序列 |
| 单车用量（路径） | `path_qty`：路径上各层相对父件 `qty` 连乘 |
| 供货总成汇总 | 按 snapshot × L0 节点聚合 |

侧栏 **就挂在这里，不要挪**：焊接工程 → 材料清单 → **零件用在哪**，与 **产品结构** 并列（`catalog.json` 里 `menu:bom-structure` 的下一个兄弟）。禁止挂到工程变更、核价、或产品结构的子页。

---

## 1. 业务是什么

工艺/采购/核价经常问的是反方向：

- 这个冲压件改号或废止，会碰到哪些供货总成、哪些项目？
- 这个分总成还挂在哪几个 L0 下面？
- 这个标准件/胶在树上出现了多少次？

现网产品结构已经能从某个 L0 **往下**看。本文补 **往上**看，且范围默认是 **全平台现网清单**（可再筛基地 / 项目 / 版本），不是只在打开的那一棵树里找。

不回答价、不指定供应商、不代替工程变更。

---

## 2. 现网约束（不要另造树）

真相只在 `bom_nodes` 邻接表：

| 事实 | 含义 |
|------|------|
| `parent_id` | 父节点；L0 为空 |
| `level` | 0 供货总成 / 1 一级 / 2 二级（现网深度） |
| `qty` | **相对父件**用量；缺省解析为 1 |
| 清单头唯一键 | `location` + `vehicle_model` + `bom_version` |
| 匹配键 | 与冲压/钢价一样用 `part_number`，不存 `part_id` |
| 同一零件号 | 可出现在多棵 L0、多份 snapshot |

现有索引 `ix_bom_node_snapshot_part_number`（`snapshot_id`, `part_number`）不能服务「只按零件号全库查」。落地时在 `bom_nodes.part_number` 上加 `ix_bom_node_part_number`。

```text
产品结构（往下）          零件用在哪（往上）
L0 供货总成               查询零件号
  └─ L1                   每一次挂载 → 直接父件 → … → L0
       └─ L2
```

---

## 3. 行业口径落到本平台

| ERP / PLM 惯例 | 本平台 |
|----------------|--------|
| 物料 where-used | 一个查询框。默认按零件身份模糊（全码 / 4 位短码 / 名称，见 §5）；可选改按内部号精确匹配 |
| 单层 / 多层 | `depth=single` 只出直接父件；`depth=multi`（默认）出到 L0 的完整路径 |
| 顶层汇总 | 按 **snapshot × L0 节点 id** 聚合路径条数与 `path_qty` 之和 |
| 工厂 / BOM 版本 | 筛 `location` / `vehicle_model` / `bom_version` / `status` |
| 替代 BOM | 不同 `bom_version` 必须分行，禁止混成一行 |
| 循环件 | 沿父最多走 8 步（大于现网 3 层）；路径上重复 `node_id` 则 `has_cycle=true` 并截断 |

**默认清单状态：`active`。** 草稿、归档要用户显式改筛才会进入结果。第一期不按月份 as_of 裁树。

**禁止**把不同 `location` 或不同 `vehicle_model` 的 `path_qty` 加总成 HUD 上的「单车用量」。HUD 只报件数（命中节点、清单数、项目数、L0 数）。用量只出现在路径行和「同一 snapshot 的 L0 汇总行」。

---

## 4. 用量

与采购价格协议、总成核价同一套：

```text
path_qty = Π (路径上自查询节点到 L0 各节点的 qty)
空 qty 按 1
```

| 字段 | 含义 | 展示 |
|------|------|------|
| `qty` | 该节点相对父件 | 路径每一层都带 |
| `qty_unit` | 多为 `pcs`；胶可能是 `mm` | 原样带出；单位不一致时 **禁止** 把该路径的 `path_qty` 与其它 `pcs` 路径在 L0 行里加总，该 L0 行 `qty_unit_mixed=true`，用量格显示 `/` |
| `path_qty` | 相对该路径 L0 的单车用量 | 路径行必带 |
| `total_path_qty` | 同一 snapshot、同一 L0 下各路径 `path_qty` 之和 | 仅单位可加时有值 |

查询件自己就是 L0：路径长度 1，无父，`path_qty` = 该节点 `qty`（常见 1）。汇总里它仍是供货总成。

---

## 5. 查询规则

查询框 **一个输入**，API 字段 `query`。`match` 决定怎么用这段字，两种键不同时混用。

### 5.1 `match=part`（默认）：零件号 + 短码 + 名称，模糊

去空白后为空 → 400。年份 / 年月写法（`is_temporal_part_number_token`）不当短码。

`LIKE` 片段必须 `escape_like_fragment`（现网 `app/common/part_number.py`），禁止把用户输入的 `%` `_` 当通配符。

命中 = 下列 **任一**（同一节点只计一次）：

| 输入长什么样 | 怎么匹配 | 例 |
|--------------|----------|----|
| 零件号全码或中间片段 | `part_number` 规范化大写后 `LIKE %TOKEN%` | `551001137AA`、`1137AA` |
| **恰好 4 位数字** | **只**按短码：零件号数字段末 4 位等于该串（与 `short_part_number_digits` / 列表 `shortPartNumber` 一致）。**禁止**再 OR `part_number LIKE`（否则中间夹着的四位会误伤）。不必扫名称 | 输入 `1137` 命中 `551001137AA`；号里别处有 `1137` 不算。`2026` 不当短码 |
| 名称（含汉字） | `part_name` **不转大写**，`LIKE %原文%` | `铰链`、`左后门上铰链` |
| 短码不够 4 位的纯数字 | 不当短码；只走零件号 `LIKE` | `137` 可能扫得很宽，靠 2000 上限拦住 |

最短长度：

| 输入 | 门槛 |
|------|------|
| 恰好 4 位数字短码 | 允许 |
| 其它 | 至少 **2** 个字符（避免单字「板」「胶」扫爆） |

短码在 SQL 里不要只写 `part_number LIKE '%1137%'`。落地可用：规范化后取数字末四位再等值（SQLite 可用表达式或查出候选后在 Service 过滤）。名称 `LIKE` 前导通配，btree 帮不上；靠 2000 上限 + 基地/项目/版本缩小范围。`ix_bom_node_part_number` 仍加，给全码等值/后缀不那么糟的情况，不假设模糊都能走索引。

### 5.2 `match=internal_number`：内部号精确

`internal_number` 去空白后等值，不再用零件号/名称。空则 400。

### 5.3 公共

| 规则 | 说明 |
|------|------|
| 高扇出 | 短码、短名称、标准件/胶允许很多行。去重后命中节点 **> 2000** → `BusinessException` 409，要求加基地/项目/版本或把名称写长一点 |
| 无命中 | 200 + 空列表 + 摘要全 0，不是 404 |

筛选均可空（空 = 不限制该维），与现网材料清单级联筛同一套基地 → 项目 → 版本。`status` 默认 `active`；未传 = 仅生效；传 `all` = 不限。

---

## 6. 算法（第一期无新结果表）

不建闭包表、不物化路径、不落库反查结果。现网深度固定，交互式查询。

1. 规范化 `query`；校验 `match` / `depth` / 最短长度。
2. Repository：JOIN `bom_snapshots` 套筛选；`match=part` 按 §5.1 模糊（短码按数字段末四位）；`match=internal_number` 等值。先对去重 `node.id` 做 `COUNT`，超 2000 则停。
3. 对命中节点 **按层批量取父**（`id IN (...)`，最多 8 轮），禁止 N+1，也禁止为每个 snapshot 加载整棵树。
4. Service 拼路径、连乘、标循环、聚 L0 行。
5. 返回完整 VO。不分页。导出与查询同一套结果，无 `ApiResponse`。

超深或超时后再议递归 CTE / 闭包表；第一期不要预支。

---

## 7. API

切片仍是 `bom`。Router 只取参、调本切片 Service。

| 方法 | 路径 | 响应 |
|------|------|------|
| GET | `/api/bom/where-used` | `ApiResponse[BomWhereUsedVO]` |
| GET | `/api/bom/where-used/export` | Excel 下载 |

Query（`BomWhereUsedQuery`）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `query` | 是 | 查询框原文；`match=part` 时可以是全码、短码或名称 |
| `match` | 否 | `part`（默认，模糊） / `internal_number`（精确） |
| `location` | 否 | 基地 |
| `vehicle_model` | 否 | 项目 |
| `bom_version` | 否 | 版本 |
| `status` | 否 | 默认 `active`；`all` 不限 |
| `depth` | 否 | `multi`（默认） / `single` |

级联下拉复用 `GET /api/bom/filters/cascade`，把本页 view 权限加入该接口的 `require_any_perm`。

### 7.1 `BomWhereUsedVO`

- `query`：回显去空白后的原文、规范化 `token`（零件号模式大写；名称模式保持原文）、`match`、`depth`、各筛
- `summary`：`hit_count`、`snapshot_count`、`vehicle_model_count`、`l0_count`
- `paths`：`list[BomWhereUsedPathVO]`
- `l0_rows`：`list[BomWhereUsedL0RowVO]`

`BomWhereUsedPathVO`：

- `snapshot_id`、`location`、`vehicle_model`、`bom_version`、`snapshot_status`
- `nodes`：自 **查询件到 L0** 的有序列表（向上）。每项含 `node_id`、`parent_id`、`level`、`part_number`、`part_name`、`internal_number`、`qty`、`qty_unit`、`qty_text`、`node_role`、`is_supply_unit`、**`sketch_url`**（该节点自己的简图，相对 `UPLOAD_DIR`；空就是空，禁止拿冲压工艺图或其它 snapshot 顶替）、以及悬停要用的 `material` / `thickness_text` / `material_mill` / `part_weight` / `weld_info` / `remark` / `excel_filename` / `excel_sheet_name` / `excel_row`
- `path_qty`、`path_qty_unit`（取查询节点的 `qty_unit`）
- `l0_node_id`、`l0_part_number`、`l0_part_name`、`l0_internal_number`、**`l0_sketch_url`**
- `has_cycle`

`BomWhereUsedL0RowVO`：

- 清单三维 + `snapshot_id` + `status`
- `l0_node_id`、`l0_part_number`、`l0_part_name`、`l0_internal_number`、`l0_seq_no`、**`l0_sketch_url`**
- `path_count`、`total_path_qty`（可空）、`qty_unit_mixed`

金额、供应商、采购对象种类 **禁止**进本 VO。跳转产品结构用 `snapshot_id`（现网 `#/bom-structure?snapshot_id=`）。

单层模式：`nodes` 仅查询件 + 直接父（查询件为 L0 则仅自身）；`l0_rows` 仍按真正的 L0 聚合（单层时若父不是 L0，L0 仍沿父取到，避免汇总缺终端总成）。若实现成本高，单层可只填 `paths`、`l0_rows` 留空并在文档落地时二选一——**选定：单层也填 `l0_rows`**，多走几步取根，不把中间件当成终端。

---

## 8. 权限与页面

落地时同一套码前后端一起加（流程见权限设计 §0，树以 `catalog.json` 为准，不要把树抄进本文）。

| 码 | 用途 |
|----|------|
| `menu:bom-where-used` | 侧栏文案必须是「零件用在哪」；放在 `menu:bom-material-list` 下、`menu:bom-structure` 之后 |
| `op:bom-where-used:view` | 查询 API |
| `op:bom-where-used:export` | 导出 |

Hash：`#/bom-where-used`。模块：`static/js/features/bom/material/where-used/`（`template.js` + `index.js`），与产品结构并列。

界面：

- 查询条：一个输入，占位「零件号、4 位短码或名称」；匹配方式默认「零件」（模糊），可改「内部号」；加基地/项目/版本 + 状态 + 单层/多层。
- HUD 四卡：命中节点 / 材料清单 / 项目 / 供货总成。
- 页签 **路径**（默认）、**供货总成**（第一期都做）。
- 供货总成表：L0 简图缩略图 + 操作列「打开产品结构」；禁止整行点击进明细。
- 超上限：Toast + 文案要求缩小范围。无命中：空态。
- 样式走 HUD 密表；路径主区按 §8.1 出图，不要做成纯文字表。

导出 Excel 两个页签：路径明细、供货总成汇总；文件名含查询串与导出时刻；数字单元格写用量，禁止把用量写成文本。第一期 Excel **不贴图**（阅读看页面）；列里可带 `sketch_url` 相对路径备查。

### 8.1 路径页：挂在哪一层就画出那一层

人要看的是「这个件挂在哪、上面长什么样」，不是再读一列零件号。

每一条路径从左到右（查询件 → 直接父 → … → L0），**每一级一张简图卡**：

```text
[本零件简图]  →  [一级/分总成简图]  →  [供货总成简图]
 短码 + 名称      短码 + 名称           短码 + 名称
 相对父件用量      相对父件用量          单车 path_qty
```

规则：

| 项 | 做法 |
|----|------|
| 图从哪来 | 只用该路径上 **这个 `bom_nodes` 的 `sketch_url`**。访问 `/uploads/{sketch_url}`，与产品结构卡同一套 `sketchSrc`。有二级时图在 L2、L1 常空——空就显示「暂无图」，**禁止**用冲压工艺简图、别的总成、或同号其它节点的图顶上 |
| 有图 | `<img loading="lazy">`，`object-contain`；点击放大（遮罩看原图），Esc/点遮罩关闭 |
| 无图 | 等高占位 +「暂无图」+ 短码，禁止裂图图标 |
| 层级标签 | 卡上标明 L0 / L1 / L2（或「供货总成 / 一级 / 二级」），避免认错方向 |
| 单层 | 仍出查询件 + 直接父两张卡（查询件是 L0 则一张） |
| 多条路径 | 一条路径一块横条，条与条分开；条头写基地 × 项目 × 版本 |
| 悬停 | 见 §8.2。卡面保持短码+图，明细不上卡面堆字 |

路径页第一屏必须能看见图。不要默认折叠成表格再点开才出图。

### 8.2 鼠标移上去：浮层出节点信息

卡面只认图。**指针进入路径卡或供货总成缩略图**，贴鼠标出浮层（对齐产品结构图 `bomVizPreview`：`position:fixed` 跟鼠标，避开视口边缘）。移开即关。键盘 Tab 到卡上同样出浮层（贴该卡，不跟鼠标）。

禁止只用原生 `title` 当详情（一行截断，采购/工艺读不够）。

浮层字段（空行不渲染）：

| 对人 | 来源 |
|------|------|
| 层级 | L0 供货总成 / L1 一级 / L2 二级 |
| 短码 · 零件号 · 名称 | 现网短码规则 + `part_number` + `part_name` |
| 内部号 | `internal_number` |
| 相对父件用量 | `qty_text` 优先，否则 `qty` + 单位 |
| 本路径单车用量 | 仅查询件那张卡带 `path_qty` |
| 材料 / 料厚 / 厂家 / 单件重量 | 节点字段 |
| 焊接信息 / 备注 | 原文，浮层内可滚动，不要截成省略号就完 |
| 材料清单位置 | `excel_filename` · 表名 · 行号（核对原件） |

浮层里可再放一张小简图，与卡面同一 `sketch_url`。点击卡仍是放大原图；悬停不抢点击。浮层 `pointer-events: none`，避免挡下一张卡。z 与抽屉同级习惯：浮层高于表，低于放大遮罩。

---

## 9. 分层（落地时）

```text
Router  GET /api/bom/where-used
   → BomWhereUsedService（拼路径、连乘、聚合、超限 409）
      → BomNodeRepository / BomSnapshotRepository（§5 匹配 + 按 id 批取父）
```

不新建表。不写 Parser。不调 costing。Orchestrator 用不上。

---

## 10. 明确不做（第一期）

- 闭包表、路径缓存、异步任务。
- BOM 有效期 `as_of`、按月裁树。
- 拼音、同音、分词、正则；用户输入里的 `%` `_` 不当通配符。
- 反查结果落库；改导入；改爆炸树 API。
- 在本页改零件、做工程变更切点、带出核价或合同价。
- 跨项目加总「单车用量」。
- 把菜单挂到工程变更 / 核价 / 产品结构子菜单。
- 用别的表的简图顶替本节点空图。

---

## 11. 金标准（落地后用现网 T13J 对）

以当时生效的芜湖 T13J 材料清单为准；件数随导入变，规则不变。

| 查询 | 期望 |
|------|------|
| `551001137AA`（多层、仅生效） | 与短码 `1137`、名称片段（该件中文名里连续几字）命中同一批节点（可多路径、多 L0） |
| 4 位短码 | 只认数字段 **末** 四位；`2026` 不搜 |
| 名称 `铰链` | `part_name LIKE %铰链%`；若超 2000 则 409 |
| 单字 `板` | 400，提示至少 2 个字或 4 位短码 |
| 某个 L0 零件号 | 至少一条路径长度为 1；汇总含自身 |
| 无内部号标准件/胶（如 `B11-4102613`） | 允许高扇出；未超 2000 则全部列出；超则 409 |
| 不存在的零件号 / 名称 | 空结果 |
| 同一 L0 下两处挂同一零件号 | 两条路径；该 L0 行 `path_count=2`，`total_path_qty` 为两处连乘之和（单位可加时） |

---

## 12. 修订

| 日期 | 说明 |
|------|------|
| 2026-09-16 | 初稿：全平台现网 BOM；路径 + L0 汇总；不改代码 |
| 2026-09-16 | 菜单对人名定为「零件用在哪」，不用「多级反查」 |
| 2026-09-16 | `match=part`：全码/片段 LIKE、4 位短码（数字段末四位）、名称 LIKE；查询字段改 `query` |
| 2026-09-16 | 钉死：恰好 4 位数字只走短码等值，不 OR 零件号 LIKE |
| 2026-09-16 | 菜单锁定材料清单下与产品结构并列；路径页各级必须出本节点简图 |
| 2026-09-16 | 悬停浮层出节点信息，不用原生 title 凑合 |
| 2026-09-16 | 落地：查询 API、导出、材料清单菜单页 |
