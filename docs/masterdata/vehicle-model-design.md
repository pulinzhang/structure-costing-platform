# 项目 — 设计定稿

> 状态：**本切片已落地**（写门禁、列表筛、引擎名单、界面「项目」、直接下一跳复合外键）  
> 界面：**项目**。库字段：`vehicle_model`。  
> 基地见 [location-design.md](location-design.md)。**基地是绝对上游**；本文依赖基地。  
> 引用保护见架构宪法 **§4.3**（谁引用谁负责；修改与删除同时支持）。

---

## 0. 一句话

> **项目挂在已有基地上，只在项目下增加：上传页 Excel（模板里写基地，页面不选手选），或一览表抽屉手工填。下游找不到：停止，来一览表补。工艺确认表只选文件，代号解析后由项目行带出基地，不能立项；布点/BOM 只核对已选项目。代号入库一律大写。**

---

## 1. 为什么做

现网没有项目实体，`vehicle_model` 由 Excel 发明。引擎按该基地下出现过的代号全部进入计划。停产项目不该再算。项目必须有生效、失效；日后特殊处理挂在项目上，不写进 costing 的 `if`。

没有基地，不能有项目。裁决「这座基地在不在」只问 [location-design.md](location-design.md)。

---

## 2. 已定规则

| # | 规则 |
|---|------|
| P1 | 项目只在本文。基地归 [location-design.md](location-design.md) |
| P2 | **不是绝对上游。** 创建、引入、核算都必须先有基地。禁止依赖冲压/BOM/核价去发明项目 |
| P3 | **立项只在项目切片。** 一览表抽屉手工增加，或上传页 Excel。上传页**不选手选基地**，基地写在模板列里。对不上已登记基地（含别名）、或基地已禁用 → 该行失败，不代建基地。找不到就回一览表补。禁止下游代建、禁止 `get_or_create`、禁止启动或脚本从下游 `DISTINCT` 灌入 |
| P4 | 没有已启用的基地行，不能插入项目。`location` = 基地规范名。本表声明 `ForeignKey("locations.location", ondelete="RESTRICT", onupdate="RESTRICT")`（宪法 §4.3）；基地改主键/删除不查本表。立项走 `LocationService.require_enabled`（抽屉与上传同一套）。禁用后已有项目行不删、不级联改生效/失效 |
| P5 | 工艺确认表能识别代号，解析后走 `require_introducible_by_code`（唯一可引入行带出基地），**不能当项目主数据的上传入口、不能立项**。布点/BOM 只核对已选项目。立项 Excel 只在项目上传页。工艺**不要求**已有布点（冲压厂可以只有工艺确认表，见 APQP） |
| P6 | 按项目引入：布点 / BOM **必选**基地 + 该基地下项目。**工艺确认上传只选文件**，不选手选基地、不选手选项目；代号从文件解析，基地由项目行带出 |
| P7 | 引擎：基地牙过了之后，本期项目名单来自本文，不从零件表枚举 |
| P8 | **生效必填，失效可空**（年+月；空 = 尚未失效）。该月可引入 = 项目自身已生效、未失效，**且** 基地已启用（调 [location-design.md](location-design.md)，不在本文重写基地判定）。不做暂停。**未到生效月不准传工艺 / 布点 / BOM**（无年无月用墙钟月问 `require_introducible`）。模具单价、检具费等项目档案不看生效月，见 §6.0 |
| P9 | 代号创建后不改。所属基地创建后不改。第一期不做项目政策表、不做项目别名 |
| P10 | **修改与删除同时支持，被引用则由数据库拒绝。** 改生效/失效、当前供货台数是改非主键，外键不管。改主键（代号或所属基地）与删除只动自己；仍被直接下游引用 → `IntegrityError` → `BusinessException("仍被引用，不能修改")` / `BusinessException("仍被引用，不能删除")`。拦的是子表 `ON UPDATE RESTRICT` + `ON DELETE RESTRICT`，不是项目去 `count` 零件/BOM。产品不提供改代号/改所属基地（P9）；子表仍必须同时声明 `onupdate="RESTRICT"`，禁止只拦删除 |
| P11 | 不从下游表 `DISTINCT vehicle_model` 发明自己 |
| P12 | **外键只加在设计图直接下一跳（宪法 §4.3）。** 按 `(location, vehicle_model)` 引入的源头表声明复合 `ForeignKey` 指向 `vehicle_models`（`RESTRICT` / `RESTRICT`）。禁止给全库同名字段再挂一套（加工费 / 核价结果 / 文件溯源 / LLM 不是下一跳）。项目 Model **禁止** `relationship` / import 子 Model。不发明项目、不改代号含义 |
| P13 | **代号一律大写。** 手工、上传、文件核对、落库都走 `normalize_vehicle_model`（去中文/圈号后 `str.upper()`）。`t13j` 与 `T13J` 是同一代号。不要另写第二套大小写规则 |
| P14 | **历史行允许不正确。** 本平台是新项目，不为脏数据写收口、不为历史开例外。新写入必须规范名 + 大写代号。禁止改写已有业务列去迁就外键。加 FK 时对不上的脏行：删掉或按正确口径重传，禁止批量改写成规范名/大写。读路径不做项目别名展开：筛 `T13J` 对不上历史 `t13j` 行，接受 |
| P15 | **同一代号可挂不同基地，是不同项目行。** 青岛 `T13J` 与大连 `T13J` 并存。写路径和下拉必须先选基地。未选基地时筛选项是各基地代号并集（同名只出现一次） |
| P16 | **当前供货台数**挂在项目行上，单位 **台**，整数 ≥ 0，默认 0。本期只录入 / 导入导出 / 一览展示，**不**从下游产量自动累加，**不**在本文算模具费。日后与模具单价「分摊万台」等上限比较（万台 × 10000 = 台）；到达上限则不再分摊——比较与停摊写在费用切片 |

冲压工厂不是项目，见 [supplier-design.md](supplier-design.md)。工艺版本、BOM 版本也不是项目。  
钢价、冲次单价无项目，走基地设计。

Excel「项目代号」仍解析到 `vehicle_model`，经 `normalize_vehicle_model`（含大写，P13）。规范化后的代号才入库、才和本表比对。

---

## 3. 位置

```
基地               ★ 绝对上游
    │
    ▼
本文 项目          引用基地；没有基地不能建、不能引入
    │
    ▼
stamping / bom / costing / dashboard
```

下游继续存 `location` + `vehicle_model` 字符串。**新写入** = 规范名 + 规范化大写代号。库里已有行允许仍是别名或小写（P14），读路径不为此做第二套展开。不做全库整型 FK。同一代号在不同基地是不同行（P15）。

引用保护（宪法 §4.3）：**子声明、父不知；只拦直接下游。** 设计图上下一跳的业务表声明复合外键指向本表；项目切片不 `count` 子行、不 import 子 Model。改主键或删除只动自己，仍被引用则引擎拒绝。间接下游（结果表、日志、溯源）不挂外键。禁止给全库同名字段再挂父表外键。

只按 `location` 写的路径（钢价、冲次单价）不过本文。  
按 `(location, vehicle_model)` 写的路径：先过基地设计，再过本文。

---

## 4. 切片与入口

| 项 | 定稿 |
|---|------|
| 切片 | `masterdata`（与基地同一切片）。宪法 §4.1 上游 / 基础数据已含 `masterdata` |
| 代码 | `app/models/masterdata/vehicle_model.py` · `routers/masterdata/vehicle_model/` · `services/masterdata/vehicle_model/` · `repositories/masterdata/vehicle_model/` · `parsers/masterdata/vehicle_model_parser.py`；前端 `static/js/features/masterdata/vehicle-model/{upload,list}/` |
| 表 | `vehicle_models`（复合主键 `(location, vehicle_model)`，两列皆 `String(50)`，与现网业务列同宽） |
| HTTP | `/api/masterdata/vehicle-models` **只给项目两页**：列表 / 手工创建 / 改生效失效与当前供货台数 / 删除 / **下载模板 / 上传 / 一览导出**。`GET ""` → `ApiResponse[VehicleModelListVO]`（基地卡 + 全部行，服务端不按 `location` 裁切）；`POST ""` 创建（主键冲突 → 「该基地已有此项目」）；`GET /template`；`POST /upload`；`GET /export`（可选 `location=`，列与模板相同）；`PATCH` / `DELETE /{location}/{vehicle_model}`（路径编码中文基地）。下游上传/计算/列表下拉**不另开**这套 HTTP：各切片沿用现有接口，Service 内调本切片。避免工艺上传权限绑 `menu:vehicle-model-upload`。一览表**禁止**再打基地页 HTTP |
| 前端 | 见本节 4.1～4.6。侧栏 **项目** 是二级分组：叶子 **上传** + **一览表**（对齐加减价政策 / 基准价格） |

基地 Model **禁止** `relationship` 指向项目。项目 Service **可以**调 `LocationService`（下游组合上游）；基地 Service **禁止** import 项目。

---

### 4.1 侧栏位置

主数据分组下，「基地」单叶之后是 **二级分组「项目」**（对齐加减价政策：父级无页面，两片叶子）。不要把上传和一览合成一个 `#/vehicle-model`，也不要另开一级侧栏分组：

```
仪表盘
冲压工程
焊接工程
一事一议
核价
文件溯源
主数据
  基地              ← 单叶，不动
  项目              ← 二级分组，无 hash
    上传
    一览表
  供应商            ← 二级分组（上传 / 一览表），见 [supplier-design.md](supplier-design.md)
设置
```

侧栏 HTML（插在「基地」`</li>` 之后；嵌套 class 抄 `thicknessSubmenu`）：

```html
<li class="submenu-item has-submenu">
    <a href="javascript:void(0)" class="submenu-link" data-submenu-toggle="vehicleModelSubmenu">
        <!-- 现网同款 outline SVG + 展开箭头，对齐加减价政策 -->
        <span>项目</span>
        <svg class="w-3.5 h-3.5 ms-auto submenu-arrow" …>…</svg>
    </a>
    <ul class="submenu submenu-nested" id="vehicleModelSubmenu">
        <li>
            <a href="#/vehicle-model-upload" class="submenu-link submenu-link-nested" data-page="vehicle-model-upload">
                <span>上传</span>
            </a>
        </li>
        <li>
            <a href="#/vehicle-model-list" class="submenu-link submenu-link-nested" data-page="vehicle-model-list">
                <span>一览表</span>
            </a>
        </li>
    </ul>
</li>
```

父级**禁止** `data-page`（否则会被当成可进页面）。叶子必须 `data-page="vehicle-model-upload"` / `data-page="vehicle-model-list"`，与 `canAccessPage` → `menu:vehicle-model-upload` / `menu:vehicle-model-list` 对齐。`permissions.js` 的 `PAGE_MENU_CODE` **不必**加特例。

无对应 `menu:` 时藏叶子；两叶都无权限则空「项目」分组一并隐藏。若「基地」「项目」都空且供应商仍无链，空「主数据」一并隐藏。

入口已写入：`static/index.html`、`features/index.js` 的 `pageMeta`。

兼容：`#/vehicle-model` → `vehicle-model-list`（与现网 `#/bom` → `bom-upload` 同类）。

---

### 4.2 路由与 pageMeta

| 项 | 上传 | 一览表 |
|---|------|--------|
| Hash | `#/vehicle-model-upload` | `#/vehicle-model-list` |
| `pages` key | `vehicle-model-upload` | `vehicle-model-list` |
| 模块 | `static/js/features/masterdata/vehicle-model/upload/` | `static/js/features/masterdata/vehicle-model/list/` |
| 顶栏标题 | 项目上传 | 项目一览 |
| `en` | `PROJECT UPLOAD` | `PROJECT` |
| `breadcrumb` | `['主数据', '项目', '上传']` | `['主数据', '项目', '一览表']` |

`app.js`：`import` 两页 + `pages[...]`；递增相关 `?v=`。

`features/index.js`：

```javascript
'vehicle-model-upload': {
    title: '项目上传',
    en: 'PROJECT UPLOAD',
    breadcrumb: ['主数据', '项目', '上传'],
},
'vehicle-model-list': {
    title: '项目一览',
    en: 'PROJECT',
    breadcrumb: ['主数据', '项目', '一览表'],
},
```

直链无对应 `menu:` → 现网守卫：`fallbackPageName()` + Toast。不要单独做登录后默认进项目页。

---

### 4.3 权限树位置

走 [permission-design.md](../permission-design.md) §0。插在 `menu:location` **之后**、`menu:settings` **之前**。树形态对齐 `menu:thickness` / `menu:base-price`：**分组 + 上传叶 + 一览叶**。**不进** `defaults` / `mandatory`。

```
menu:masterdata                          # 已有
  ├── menu:location                      # 已有，单叶
  └── menu:vehicle-model                 # 二级分组，label「项目」，无页面
        ├── menu:vehicle-model-upload    # 叶子，label「上传」
        │     ├── op:vehicle-model-upload:view
        │     └── op:vehicle-model-upload:upload
        └── menu:vehicle-model-list      # 叶子，label「一览表」
              ├── op:vehicle-model-list:view
              ├── op:vehicle-model-list:export
              ├── op:vehicle-model-list:create
              ├── op:vehicle-model-list:update
              └── op:vehicle-model-list:delete
menu:settings
```

| 码 | 用途 |
|---|------|
| `menu:vehicle-model` | 授权树分组、侧栏「项目」；不是页 |
| `menu:vehicle-model-upload` | 进上传页、侧栏「上传」 |
| `op:vehicle-model-upload:view` | 看上传页；下载模板 |
| `op:vehicle-model-upload:upload` | 提交 Excel |
| `menu:vehicle-model-list` | 进一览表、侧栏「一览表」 |
| `op:vehicle-model-list:view` | 列表 |
| `op:vehicle-model-list:export` | 导出 Excel（列与导入模板相同） |
| `op:vehicle-model-list:create` | 抽屉手工新增 |
| `op:vehicle-model-list:update` | 改生效/失效、当前供货台数 |
| `op:vehicle-model-list:delete` | 删除项目 |

CRUD：上传路由绑 `upload` 叶权限；一览写操作绑 `list` 叶对应 `op`。按钮 `can('op:…')`，不能只藏侧栏。

---

### 4.4 上传页 UI

**参照** 基准价格上传（`yishiyiyi/base-price/upload`），不是把一览表和上传挤在同一页。

- 拖拽区 + 「选择文件」+ 「下载模板」；只选 `.xlsx` / `.xls`
- **没有**采购基地下拉（基地在 Excel 列里，违反 P3 的那种「先选基地再传」不要抄）
- 主按钮红底 `#d32f2f`（本页只用这一种红）
- 提交后等本次 HTTP 结束，进度条即可；本页**没有**任务轮询。无 `task_id` 的 HTTP 契约只写在 §5.4（宪法 §五同步 Excel 封闭名单，不是漏做异步）
- 成功 Toast 后可深链一览表，不在本页画数据表

模板列见 §5.4。整单事务：任一行失败则全部不写入。

---

### 4.4.1 一览表 UI

**必须走 HUD 密表**（前端规范 §4.4），参照 `costing/stamping-part-cost/list`。目的：一眼分清各基地项目情况。不要抄基地页那种浅阶简单 CRUD。

强调红只用 `#FF1E27`，不要和 `#d32f2f` 混用。

抄这些：

- 外框 `bg-[#0A0A0C] border-[#1A1A22]`；表区 `bg-[#0A0A0E]`；工业阴影允许内联
- 表头 `text-[9px] text-[#555555]`；表体 `font-mono text-[11px]`；行 hover `bg-[#161620]` + 左侧 2px 红条
- 操作只在操作列；**禁止**整行点击、禁止行 `cursor-pointer`
- 新增 / 改生效失效与供货台数用 **抽屉**（z-index ≥ 80/85）；删除先确认
- 筛选胶囊可 `rounded-md`；**表体直角**

不要抄这些：

- 零件价那种「查询」按钮 + 高级筛选折叠（基地情况用 HUD 卡片点选即可）
- **分页**（第一期一次列出当前筛选结果；不用 `page-size.js`）
- 别名抽屉、拖拽上传区（在上传页）
- 金额 KPI 红底列（本页无单价）

**HUD：按基地分卡（必做）**

上方一块看板：**一张「全部」+ 一座基地一张卡**。卡的顺序与数字全部来自 `GET /api/masterdata/vehicle-models` 的 `VehicleModelListVO`（`locations` + `items`）。**不另开统计 HTTP，也不打基地页 HTTP**（空项目的基地必须出卡，单靠项目行拼不出来；本页用户不一定有 `op:location:view`）。

墙钟年月写在响应的 `as_of_year` / `as_of_month`。行上 `period_status` 只看项目生效/失效相对该月（未生效 / 可引入 / 已失效），**不含**基地启用。前端只汇总展示，不自己算月。

| 卡 | 口径 |
|---|------|
| 「全部」 | 可点，清除筛选。数字：项目总数、该月可引入合计（仅 `period_status=可引入` **且** 该基地已启用） |
| 基地规范名 | 主标题 |
| 禁用 | 卡片弱化；文案「已禁用」，不要装成「项目已失效」。该月可引入固定 `—` |
| 项目数 | 该基地下行数（0 也出卡） |
| 该月可引入 | `period_status=可引入` 且基地已启用的行数；禁用则为 `—` |
| 未生效 / 已失效 | 辅助数，只看 `period_status`，字更弱 |

点基地卡 = 前端筛该基地（hash 查询 `location=`，**服务端仍返回全量**）。再点同一张或点「全部」= 清空。这是规范允许的非表体行点击筛选，不是整行进明细。

**表：按基地分段**

筛「全部」时表体按 `sort_order` **分段**，每段一行基地标题（规范名 + 该段项目数；禁用段标题带「已禁用」），下面才是该基地项目行。不要把「基地」再做成与代号并列的普通列当唯一区分。筛了某一基地则只出该段，仍保留段标题。

**0 项目的基地：出卡，表里不出空段。**

| 区域 | 内容 |
|---|------|
| 顶 HUD | 「全部」+ 各基地卡；右侧「导出 Excel」（`op:vehicle-model-list:export`）+「新增项目」（`op:vehicle-model-list:create`）。不放上传按钮 |
| 胶囊 | 当前筛选：全部基地 / 某规范名 |
| 段标题 | 基地规范名（禁用则附「已禁用」） |
| 表列 | **项目代号**是主信息（更大更亮）。生效年月、失效年月、**当前供货台数（台）**、该月状态（未生效 / 可引入 / 已失效，只看项目期）用钛灰字，**不要**绿/橙徽章抢代号 |
| 操作列 | 编辑生效/失效与供货台数、删除 |
| 新增 | 抽屉：基地（必选，下拉 `list_enabled()`）、项目代号、生效年+月（必填）、失效年+月（可空）、当前供货台数（必填，默认 0，单位台）。代号经 `normalize_vehicle_model`（含大写）；空/纯中文/`UNKNOWN`/`未知车型` 拒收。主键已存在 → Toast「该基地已有此项目」 |
| 编辑 | 抽屉：基地与代号只读；改生效/失效、当前供货台数 |
| 删除 | 确认后 DELETE；仍被引用则 Toast「仍被引用，不能删除」 |

年月展示用 `fmtYear` / `fmtMonth`（`2026年`、`07月`），禁止 `2026-07`。失效空则 `—`（尚未失效）。

**不分页**：`GET` → `ApiResponse[VehicleModelListVO]`，一次全量。点卡只切表体。hash `?location=` 仅作深链初筛。排序：基地 `sort_order`，同一基地内 `vehicle_model` 字母序。第一期无手改排序。

下游找不到时 Toast 带 `#/vehicle-model-list`，**不要**在工艺/计算页内嵌创建表单。

---

### 4.5 下游页：不改菜单位置

布点、BOM、加工费、核价等**侧栏条目不动**。这些页控件文案为 **项目**（与一览表同一实体；历史「车型 / 配套车型」同一字段）。**工艺确认上传无项目框。**

下拉 / 筛选项读本文，禁止用业务表 `DISTINCT vehicle_model` **当选项来源**（P11）。零件列表、加工费一览等页内 HUD「项目数」仍是**本表 DISTINCT**（这页有多少种代号），不要改成主数据行数。

写路径必须先选基地，再出该基地项目（P15）。未选基地时筛选项可以是代号并集。**工艺确认上传例外**：不选手选，用 `require_introducible_by_code` 由唯一可引入行带出基地。

P5 / P6 已覆盖的路径：

| 曾 | 现网 |
|---|------|
| 工艺上传只选文件，项目从文件识别 | **只选文件**；`require_introducible_by_code`（墙钟月）用唯一可引入行带出基地。抽不出 / 未登记 / 该月不可引入 / 同代号多基地可引入 → 硬停。**仍不要求已有布点**。文件识别 ≠ 文件立项 |
| 模具布点「手工录入」项目 | 下拉（墙钟月 `list_introducible`）。无布点的冲压厂不走此页 |
| 模具单价 / 检具费 | 下拉 `list_registered`（已登记即可，允许 SOP 前建档） |
| 引擎「配套车型」= 零件表去重 | 本文 `list_introducible`。见 [costing-engine-design.md](../costing/costing-engine-design.md) |

仪表盘快捷入口**不**加「项目」。仪表盘筛选项走 `list_filter_codes`（无年时即已登记并集）。

---

### 4.6 入口对齐（已落地）

侧栏二级、两页 `pageMeta` / `app.js`、权限树 `menu:vehicle-model*`、[location-design.md](location-design.md) §4.1、引擎名单、界面「项目」、直接下一跳复合外键均已接上。

APQP 文档若仍写「只选基地、文件立项」，以本文为准。

---

## 5. 表结构

### 5.1 `vehicle_models`

复合主键 `(location, vehicle_model)`。业务表继续存这两个字符串，不做全库整型 FK。

| 列 | 说明 |
|---|------|
| `location` | 基地规范名，主键之一。`ForeignKey("locations.location", ondelete="RESTRICT", onupdate="RESTRICT")` |
| `vehicle_model` | 项目代号，主键之一，`String(50)`，创建后只读。入库值 = `normalize_vehicle_model` 之后（**大写**） |
| `effective_year` | 生效年，`Integer`，必填 |
| `effective_month` | 生效月，`Integer` 1–12，必填 |
| `expiry_year` | 失效年，可空。与 `expiry_month` 必须同空或同有 |
| `expiry_month` | 失效月，可空，1–12 |
| `current_supplied_units` | 当前供货台数，`Integer`，**必填**，≥ 0，默认 0，单位 **台**（不是万台）。手工/Excel 录入；**禁止** `float` / `Decimal` |
| 审计 | `AuditUserMixin` |

禁止 `is_paused` / `is_enabled`（启用/禁用是基地的事；期内停用靠改失效）。禁止逻辑删除 / 软删冒充 P10。

**期别比较（闭区间，对齐 [effective-period-design.md](../costing/effective-period-design.md) 的「含」）：**

```text
已生效  = (year, month) >= (effective_year, effective_month)
未失效  = 失效两列皆空  或  (year, month) <= (expiry_year, expiry_month)
可引入  = 已生效 且 未失效 且 基地已启用
```

失效有值时必须 `(expiry_year, expiry_month) >= (effective_year, effective_month)`，否则 `BusinessException`。  
禁止存 `date` / `datetime` 当生效期：系统没有「日」口径。

项目 Model **禁止** `relationship` 指向冲压/BOM。基地 Model **禁止** `relationship` 指向本表。

### 5.2 直接下一跳外键（宪法 §4.3）

子表声明，父不知。复合外键指向 `vehicle_models(location, vehicle_model)`：

```python
ForeignKeyConstraint(
    ["location", "vehicle_model"],
    ["vehicle_models.location", "vehicle_models.vehicle_model"],
    ondelete="RESTRICT",
    onupdate="RESTRICT",
)
```

`onupdate` 与 `ondelete` **必须同时声明**。禁止只拦删除。禁止 `CASCADE`（独立主数据，不是附属行）。

| 加 FK（直接下一跳） | 不加 FK（间接 / 副本 / 无项目列） |
|---|---|
| 冲压零件、模具布点、模具单价、检具费、BOM 快照、包装运输费 | 加工费 / 模具费 / 焊接费 / 零件核价 / 成品核价结果、计算日志、文件溯源、LLM；采购对象清单 / 焊接工艺拆解（从 BOM 生成）；年度零件价 / 焊接单价 / 基价 / 冲次 / 废料（无项目列或不是下一跳） |

新直接子只改子 Model，项目的修改/删除代码不变。外键随 Model / `create_all` 建表落地；对不上本表 PK 的脏行禁止批量改写成规范名/大写，禁止从下游 `DISTINCT` 灌入，应删掉脏行或按正确口径重传。

钢价 / 冲次单价 / 废料价、加工费与核价结果等**不是**本表下一跳：不加本表外键。读历史别名仍走基地设计 `expand_for_query`（那是基地读路径，不是本文去改业务行）。

### 5.3 不做的表与入口

| 不做 | 原因 |
|---|------|
| 项目别名 | 代号创建后不改；业务 Excel 前缀/圈号由 `normalize_vehicle_model` 处理，不维护第二套写法 |
| 项目政策 | P9，第一期不做 |
| 暂停 | 只有生效/失效。期内不用靠布尔开关；要停引入就改失效 |
| 按销量自动累加供货台数 | P16：本期只手工/导入；累加与停摊在费用切片日后做 |
| 启动 / 脚本灌入 | 禁止 `ensure_seed_if_empty`、禁止 `scripts/backfill_vehicle_models` 一类从零件/BOM `DISTINCT` 灌入。一百多个项目用上传页 Excel，不要从下游发明 |

### 5.4 上传页模板

Parser 只被本切片 Service 调用。页面**不传** `location`。列（表头中文，第一行）：

| 列 | 必填 | 规则 |
|---|------|------|
| 基地 | 是 | `LocationService.require_enabled`（先 `resolve_canonical`）；对不上或已禁用 → 该行失败，文案去基地页。禁用基地**不能立项** |
| 项目代号 | 是 | `normalize_vehicle_model`（含大写）；空/纯中文/`UNKNOWN`/`未知车型` → 失败 |
| 生效年 | 是 | 整数年 |
| 生效月 | 是 | 1–12 |
| 失效年 | 否 | 与失效月同空或同有 |
| 失效月 | 否 | 1–12；有值时失效 ≥ 生效 |
| 当前供货台数 | 否 | 单位台；空 = 0；必须为 ≥ 0 整数，拒绝小数与负数 |

文件内按规范化后的 `(location, vehicle_model)` 去重：

- 同一主键、生效/失效/当前供货台数与首次出现相同 → 后行跳过（计入 `skipped_count`）
- 同一主键、生效/失效或当前供货台数不同 → **整单失败**（禁止猜哪一行）
- 库里已有该主键 → 跳过、**不覆盖**生效/失效/当前供货台数（改期或改台数走编辑抽屉）

整单一个事务，任一行失败（含上条冲突、基地禁用、代号非法）则全部回滚。抽屉 `POST` 遇到已有主键 → `BusinessException("该基地已有此项目")`，不要学 Excel 静默跳过。

`GET /api/masterdata/vehicle-models/template` → `StreamingResponse`（无 `ApiResponse`）。`POST /api/masterdata/vehicle-models/upload` 只收文件，走**请求 Session**，返回 `ApiResponse[VehicleModelUploadResultVO]`（`created_count` / `skipped_count`，具名 VO），**无** `task_id`。百行名册；入口在宪法 §五同步 Excel 封闭名单。禁止改成 `start_upload`。上传页交互见 §4.4。

`GET /api/masterdata/vehicle-models/export` → `StreamingResponse`。列与模板完全相同（基地、项目代号、生效年、生效月、失效年、失效月、当前供货台数），失效空则空单元格；供货台数写整数（0 也写出）。可选 `location=` 只导出该基地；不传则全量，顺序与一览表相同。不要加「该月状态」列，否则无法再导入。已有主键再导入仍跳过、不覆盖（改期或改台数走抽屉）。

`PATCH` / `DELETE /api/masterdata/vehicle-models/{location}/{vehicle_model}`：`location`、`vehicle_model` 为路径参数（中文基地须 URL 编码）。PATCH 体含生效/失效四列 **以及** `current_supplied_units`。DELETE 无请求体。

### 5.5 一览表响应 VO

```text
VehicleModelListVO
  as_of_year, as_of_month          # 墙钟月，与 period_status 同一瞬间
  locations: list[LocationCardVO]  # list_registered 顺序，含 0 项目、含禁用
  items: list[VehicleModelVO]      # 全部项目行

LocationCardVO
  location, is_enabled, project_count, introducible_count, pending_count, expired_count

VehicleModelVO
  location, vehicle_model, effective_*, expiry_*, current_supplied_units
  period_status                    # 未生效 | 可引入 | 已失效（只比项目期与 as_of，不含基地启用）
```

`introducible_count`：该卡 `is_enabled` 且行 `period_status=可引入`。禁用卡此字段 0，前端展示 `—`。

---

## 6. 解析契约（废止 `DISTINCT vehicle_model`）

查库、门禁只发生在 **Service**（本切片或下游切片调本切片）。**禁止 Parser 调 Service / Repository**。项目上传页：Service 调 Parser 得到行，再 `resolve_canonical` / `normalize_vehicle_model` / 插入。下游工艺上传：Parser 只做 `normalize_vehicle_model`；Service 再 `require_introducible_by_code`（文件识别 ≠ 文件立项；唯一可引入行带出基地）。布点 / BOM：`require_introducible` + `assert_matches_selected`。

规范化：`normalize_vehicle_model` = 去 CJK、去 ①–⑳、strip，然后 **`str.upper()`**（P13）。空串不是项目。不做全角转换、不发明未登记代号。`青岛t13j` → `T13J`。

比较年月用元组 `(year, month)`，不要拼 `2026-07` 字符串。

### 6.0 写门禁分层

不是所有带 `vehicle_model` 的写入都问「该月可引入」。按有没有期、是不是当期业务切：

| 门禁 | 何时用 | 典型路径 |
|---|---|---|
| `require_registered` + 基地 `require_enabled` | **项目档案**：不按月引入，允许 SOP 前建档 | 模具单价、检具费 |
| `require_overlaps_year(location, vehicle_model, year)` | **只有年、没有月**：该年 1–12 月至少有一个月满足可引入（含基地启用） | 包装运输费上传、年度零件价**下载模板**；加工费 / 模具费 / 焊接费（DTO 只有年） |
| `require_introducible(..., year, month)` | **当期引入 / 按月计算** | 布点、BOM；零件核价 / 成品核价；引擎 `start_run` |
| `require_introducible_by_code(..., year, month)` | **文件识别代号、不选手选基地** | 工艺确认上传 |

无年无月的当期引入用**墙钟年月**。工艺走 `require_introducible_by_code`；布点、BOM 走 `require_introducible`（须先选基地）。**未到生效月不准传工艺**（Service 拒绝）。不要把检具费、模具单价塞进这套墙钟门禁。

下拉与门禁对齐：档案页 `list_registered`；布点 / 计算页 `list_introducible`（有年+月用用户所选，否则墙钟）；**只有年**的计算页 `list_overlaps_year`。列表筛走 `list_filter_codes`（有基地则 `list_registered`，无则代号并集）。不要把已失效项目摆进「请选择项目」（计算/布点）；档案页可以列出未生效行，便于提前建档。

### 6.1 方法

| 方法 | 行为 |
|---|------|
| `normalize` | 调用 `normalize_vehicle_model`（含大写）；空 / 占位符 → `None` |
| `require_registered(location, vehicle_model)` | 有行 → 返回规范化代号。没有 → `BusinessException`，提示去一览表（可带 `#/vehicle-model-list`）。**不看生效月**。档案写入前仍须 `LocationService.require_enabled` |
| `require_introducible(location, vehicle_model, year, month)` | ① `LocationService.require_enabled(location)` ② 有行 ③ 该月已生效且未失效 → 返回 `(规范名, 代号)`。失败文案区分：没有基地 / 基地禁用（指向 `#/location`）；没有项目 / 未生效 / 已失效（指向 `#/vehicle-model-list`）。**只给 §6.0 当期引入 / 按月计算用，不是所有写入** |
| `require_introducible_by_code(vehicle_model, year, month)` | 按代号查出全部行，筛该月可引入（含基地已启用）。**恰好一行** → 返回该行 `(基地, 代号)`。零行 → 没有 / 未生效 / 已失效 / 基地禁用。多行可引入 → 无法自动确定，去一览表。工艺确认上传用这个，不选手选基地 |
| `require_overlaps_year(location, vehicle_model, year)` | ① 基地已启用 ② 有行 ③ 该年 1–12 月与项目期（生效～失效，空失效=尚未失效）有交集 → 返回 `(规范名, 代号)`。年度零件价模板、包装运输费用这个 |
| `assert_matches_selected(selected, parsed)` | 两边都 `normalize` 后必须相等。不等 → `BusinessException`（沿用现网「文件项目为 {识别}，与填写的项目 {表单} 不一致」）。**不立项** |
| `list_introducible(location, year, month)` | 该基地该月可引入的代号，按 `vehicle_model` 排序。内部仍先确认基地已启用；已禁用 → 空列表或由调用方先 `require_enabled` |
| `list_overlaps_year(location, year)` | 该基地该年与项目期有交集的代号。内部确认基地已启用；已禁用 → 空列表 |
| `list_registered(location)` | 该基地下全部已登记（含未生效、已失效），按 `vehicle_model` 排序。档案下拉 |
| `list_filter_codes(location=None)` | 列表筛入口：有基地则 `list_registered`；无则各基地代号并集（同名一次） |
| `list_page()` | 一览表：组装 `VehicleModelListVO`（墙钟 `as_of_*`、全部基地卡、全部行 + `period_status`） |

列表筛选项必须来自 `list_filter_codes`，**禁止**再 `DISTINCT` 业务表 `vehicle_model` 当选项（P11）。筛了一个还没算过的项目 → 空表，不是丢数据。

未选基地时筛选项 = 各 `list_registered` 的代号并集（同名一次）。写路径禁止无基地只按代号落库（P15）。

写路径 cascade（已选基地且带年）：有月则 `list_introducible`，无月则 `list_overlaps_year`。**不要**再包一层分发器。

工艺上传仍**不要求已有布点**（P5）。冲压厂可以只有工艺确认表。不要把「解析后门禁」理解成「必须先有布点」。

### 6.2 写

落库只写**规范化大写代号**。文件里写「青岛t13j」：规范化后命中该基地已登记行则通过，仍落 `T13J`。

工艺确认上传：只选文件；文件解析代号后 `require_introducible_by_code`（墙钟月）带出基地。抽不出 / 未登记 / 该月不可引入 / 同代号多基地可引入 → 硬停。**不能立项**。

布点 / BOM：必选项目（P6），门禁 `require_introducible`（墙钟月），再 `assert_matches_selected`。

按月计算与引擎每个项目：`require_introducible`（用户选的年、月）。加工费 / 模具费 / 焊接费 DTO 只有年：`require_overlaps_year`。

模具单价 / 检具费：`require_enabled` + `require_registered`。

包装运输费 / 年度零件价模板：`require_overlaps_year`。

### 6.3 读

查询按库里的字符串精确匹配。比对项目主数据时双方都先 `normalize`（含大写）。本文不做项目别名展开，也不为历史小写/别名做第二套查询（P14：筛 `T13J` 对不上旧行 `t13j`，接受）。

新写入只写规范名和大写。库里已有行允许不正确。对不上的旧行自然进不了新计算。禁止全库批量改代号、禁止改写历史列去迁就外键。

未生效 / 已失效：不准当期引入、不准进引擎名单；已有结果仍可查、筛选里用 `list_registered`。

基地禁用：不准立项、不准新引入（基地设计 `require_enabled`）。已有项目行的生效/失效**不级联改**。若不能引入是因为基地已禁用，走基地设计文案，不在一览表把行状态改成「已失效」。

### 6.4 删除 / 修改

对齐宪法 §4.3：父只改/删自己；拦引用的是引擎，不是项目切片去点名子。

| 动作 | 行为 |
|---|------|
| 改生效 / 失效 / 当前供货台数 | `UPDATE` 非主键列，外键不管。校验 §5.1。**已有费用结果不改写**。重算、新计算该月仍走当时的 `require_introducible`：把失效提前等于锁死那个月的重算，要重算就先把失效改回去。改台数本身不触发模具费重算 |
| 改代号 / 改所属基地 | 产品不提供（P9）。若仍被直接下游引用，引擎 `ON UPDATE RESTRICT` → `IntegrityError` → `BusinessException("仍被引用，不能修改")` |
| 删除 | 只 `DELETE` 自己。仍被直接下游引用 → `IntegrityError` → `BusinessException("仍被引用，不能删除")` |

Service：`except IntegrityError` 后按动作翻译成上面两句。**禁止**文案点名冲压/BOM，禁止 `count` 零件 / import 下游切片。

有外键则修改（非主键）与删除必须同时提供；不是用改失效代替「未声明外键」。停产用失效；删得掉只说明没有直接下游行了。

---

## 7. 找不到 / 引擎

| 情况 | 去哪 |
|---|------|
| 没有这座基地 / 基地已禁用 | [基地](location-design.md)，不是本切片代建。禁用基地不能立项 |
| 有基地、没有该项目 | 一览表抽屉增加，或上传页 Excel |
| 有行但该月未生效 / 该月已失效 | 一览表改生效/失效；**未生效不准传工艺 / 布点 / BOM**；模具单价/检具费仍可建档（`require_registered`）；下游不代建 |
| 文件代号对不上已选项目 | 不准传，不立项 |

上传/计算页可深链 `#/vehicle-model-list`，不得内嵌创建。

引擎入口仍是 **基地 + 年 + 月**。

1. 先过基地设计：`LocationService.require_enabled`。不过则硬停。  
2. 再 `list_introducible(location, year, month)` → 本期项目名单。  
3. costing 用这份名单问工艺/BOM（加工费补算、PartCost、L0 快照过滤）。名单外的零件/BOM **不进入计划**（停产就是这个效果）。  
4. 名单空：硬停，文案去一览表，不要说「该基地没有冲压零件」。  
5. 名单有、工艺/BOM 缺：仍走现网上传/配置门禁。

L0Scope 仍来自含 L0 的 BOM 快照，但 `vehicle_model` 必须落在本期名单里；禁止 BOM 里多一个未登记/已失效代号就多算一车。

`ScopeDiscovery` 问本文 `list_introducible`，文案「项目」，不从 `stamping_parts` 去重。

---

## 8. 谁读本文 / 谁不要动

**已接：**

- 引擎 `ScopeDiscovery` / `GateChecker`：`list_introducible`；文案「项目」。见 [costing-engine-design.md](../costing/costing-engine-design.md)
- 各切片 cascade / filters：`vehicle_models` 列表筛走 `list_filter_codes`。**本页 HUD 计数**仍 `DISTINCT` 本表，不要改成主数据行数
- 工艺上传：只选文件；解析后 `require_introducible_by_code` 带出基地。**不**要求先有布点
- 模具布点上传：下拉（墙钟月 `list_introducible`）
- BOM 材料：墙钟月 `require_introducible` + `assert_matches_selected`
- 采购对象生成 / 列表：见 [bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md)。生成 **不** `require_introducible`。列表筛 `list_filter_codes`。清单头/行/日志不加本表外键
- 模具单价 / 检具费：下拉 `list_registered`；写入 `require_enabled` + `require_registered`
- 包装运输费：`require_overlaps_year`；年度零件价**下载模板**同样（价表无 `vehicle_model` 列，不加本表外键）
- 冲压加工费、模具费、焊接费：计算入口 `require_overlaps_year`。零件核价、成品核价：`require_introducible`
- `normalize_vehicle_model` 末尾 `str.upper()`（P13）
- 界面标签「项目」
- LLM：只读本表 Model（**禁止**调 VehicleModelService）。`ScopeOptionsRepository.list_vehicle_models` 读 `vehicle_models`，对齐先 `normalize`
- 直接下一跳 Model（宪法 §4.3）：复合 `ForeignKeyConstraint` → `vehicle_models`（`RESTRICT` / `RESTRICT`）。只改子表。项目 Service 删除/改主键只收 `IntegrityError`

**不要做：**

- 钢价、冲次单价、废料月度销售价（无项目，只走基地设计）。**不要**让钢价 Service 调本文
- 给加工费 / 核价结果 / 日志 / 文件溯源 / LLM 等间接列加项目外键
- 给 `stamping_parts.location`、钢价.location 加**基地**外键
- 给钢价、冲次单价、废料价、年度零件价、焊接单价加项目外键
- 改写已有业务列去迁就外键；不为脏数据写回填脚本（P14）
- 为历史小写代号做第二套查询 / 项目别名
- 基地表 / 别名 / `require_enabled`
- 供应商
- 项目切片里 `count` 下游 / import 冲压·BOM·costing 来决定能不能删
- 零件/结果页 HUD「项目数」改成主数据行数
- 包一层 `list_period_codes` 之类的下拉分发器；cascade 点名 `list_introducible` / `list_overlaps_year` / `list_filter_codes`

---

## 9. 特殊处理（预留）与当前供货台数

日后政策类特殊处理挂在项目上，第一期不做政策表。全基地口径若出现，开基地设计，不塞进项目。

政策表若落地：由该表声明指向 `vehicle_models` 的复合外键（`RESTRICT` / `RESTRICT`）。只改政策表，项目修改/删除代码不变。

**当前供货台数已落在本表列上（P16），不是政策表。**

| 项 | 定稿 |
|---|------|
| 字段 | `current_supplied_units`，单位 **台** |
| 用途 | 供日后模具费（或其它按台数分摊的费用）判断：已供货台数到达上限则不再分摊 |
| 上限从哪来 | 不在本表。模具费现网上限是模具单价上的 **分摊万台**（× 10000 = 台）。比较与停摊写在费用切片 |
| 本期 | 一览列、抽屉、Excel 模板/导出可读写。空导入 = 0。已有行 SQLite 补列默认 0 |
| 不做 | 自动按销量累加；在项目切片里算模具费；把万台写进本表 |

---

## 10. 范围

**做：** 切片 `masterdata` 项目（侧栏二级：上传 + 一览表；抽屉手工增加 + Excel 上传，模板自带基地；一览表导出列与模板相同；挂**已启用**基地、生效/失效、**当前供货台数**）；代号一律大写；同一代号可跨基地（P15）；§4.1～4.6；一览表 HUD 按基地分卡（一份 `VehicleModelListVO`）；写门禁分层（§6.0：档案 / 按年 / 当期引入）；布点/BOM `assert_matches_selected`；引擎名单问本文；工艺上传只选文件、解析后 `require_introducible_by_code` 带出基地、仍不要求布点；未生效月不准传工艺/布点/BOM；界面「项目」；直接下一跳复合外键（改主键/删除 `RESTRICT`，宪法 §4.3）。新写入必须正确；历史行允许不正确。

**不做：** 上传时选手选基地；禁用基地立项；启动或脚本从下游表灌入种子；基地表/别名；项目别名 / 第二套大小写查询；政策表；下游代建立项；改代号；改所属基地；暂停；基地禁用时改项目生效/失效；未生效月传工艺/布点/BOM；把模具单价/检具费也卡生效月；工艺绑定必须先有布点；全库整型外键；给间接列加项目 FK；改写历史业务列迁就外键；项目切片 `count` 下游；逻辑删除；手改排序；分页；生效到日；一览表再打基地 HTTP；0 项目基地在表里出空段；按销量自动累加供货台数；在本文里写模具费停摊。

侧栏「项目」与「基地」分开展示、不是同一张表。  
对基地：本表声明 `RESTRICT`，不在基地切片点名项目。  
对下游：子表声明 `RESTRICT`，不在项目切片点名冲压/BOM。被引用时改主键文案「仍被引用，不能修改」，删除文案「仍被引用，不能删除」。
