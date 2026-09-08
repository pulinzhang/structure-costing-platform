# 供应商 — 设计定稿

> 状态：**已落地（第一期）**  
> 界面：**供应商**。工艺筛选项「冲压工厂」、采购对象「合同对方」、年度价「供应商」为同一主数据，不另立工厂表。  
> 库字段（现网下游仍存字符串）：`stamping_supplier` / `supplier_name`，新写入 **全称**（与现网工艺确认表一致）。  
> 基地见 [location-design.md](location-design.md)，项目见 [vehicle-model-design.md](vehicle-model-design.md)。本文不定义基地、项目。  
> 引用保护见架构宪法 **§4.3**（一期不加业务列外键，故不提供改主键、不提供删除，只保留禁用）。

---

## 0. 一句话

> **供应商只在供应商下增加：上传页 Excel，或一览表抽屉手工填。有缩写、全称、ERP 代码，以及启用/禁用。一条可挂多条别名，用来吃工艺确认表里乱写的厂名。下游找不到：停止，来一览表或上传页补。禁止从工艺文件发明供应商。工艺落库只写规范全称，不写表头原文、不写缩写。**

---

## 1. 为什么做

现网没有供应商实体。工艺确认表「冲压承制公司」**写的就是全称**，现网 `stamping_supplier` 也按全称入库。各文件仍会乱写（多字、少字、曾用名、带括号），但规范形态是全称，不是缩写。年度价、采购对象行上 `supplier_name` 是自由文本。同一家单位多种写法，无法对 ERP。

主数据给出稳定身份：**ERP 代码** 对外系统（合同 / ERP，不进工艺列）。  
本平台规范名 = **全称**，对齐现网工艺确认、对齐基地「规范名」：点选落库、覆盖键都用它，创建后不改。  
**缩写** 只给人看（下拉旁注、窄列），不进 `stamping_supplier`。  
**别名（一条多条）** 吸收表头乱写。核对用全称 / 缩写 / 别名 / ERP，工艺落库只用规范全称。

钢厂 / 紧固件商（`material_mill`）不是本文，仍在一事一议 / 材料侧。

---

## 2. 已定规则

| # | 规则 |
|---|------|
| S1 | 供应商只在本文。不挂在项目下。不替代基地 |
| S2 | 与基地同属主数据；**不依赖** 项目 / 冲压 / BOM / 核价。按供应商写入的下游依赖本文 |
| S3 | **建档只在供应商切片。** 一览表抽屉手工增加，或上传页 Excel。下游找不到就回一览表 / 上传页补。禁止下游代建、禁止 `get_or_create`、禁止启动或脚本从下游 `DISTINCT` 插入。工艺确认表、年度价、采购对象**不能**当供应商主数据的上传入口 |
| S4 | 必填 **缩写**、**全称**、**ERP 代码**。三者各自唯一，且与别名同一解析命名空间互斥。ERP 代码创建后不改（对外身份）。全称创建后不改（本平台规范名，对齐现网工艺确认、对齐基地 B5）。缩写创建后不改（界面短名，不落工艺列） |
| S5 | 凡要点选供应商，选项只来自本文。禁止自由输入 |
| S6 | 工艺表头厂名经 `require_enabled` 解析为规范全称才准入。命中全称、缩写、ERP 代码或**任一条别名**即同一家。不能当建档入口。对上后落库写规范全称，不能按表头原文落库，也不能改写成缩写 |
| S7 | 不从下游表 `DISTINCT stamping_supplier` / `supplier_name` 发明自己 |
| S8 | **启用 / 禁用** 即可。已启用才允许新引入。不物理删除。不做生效/失效日期、不另做暂停 |
| S9 | **一期不加业务列外键，因此不准改主键、不准删除**（宪法 §4.3：不加外键则只保留禁用）。禁用不是「用禁用代替未声明外键」的权宜；是明确选择。日后若直接下一跳要加 `RESTRICT`，必须同时开放删除并改 S8 |
| S10 | **历史行允许仍是乱写的全称变体。** 新写入必须规范全称。禁止批量改写已有 `stamping_supplier` / `supplier_name`。读、覆盖删除、列表/导出筛选用 `expand_for_query` |
| S11 | **工艺确认上传写门禁（本期落地）。** 表单不选冲压工厂。Parser 抽出厂名后 `require_enabled`。抽不出 / 未登记 / 已禁用 → 硬停。对上后 **`stamping_supplier` 只写规范全称**，禁止写表头原文、禁止写缩写、禁止写 ERP。禁止从文件发明身份。布点仍不认供应商（APQP） |
| S12 | **采购对象改供应商写门禁（日后落地，同一方法）。** 行上指定或改成非空对方时必须 `require_enabled`。清空不跑门禁。禁止另写一套校验、禁止自由文本。本期供应商切片**不**提前做采购对象页 |
| S13 | **一条供应商可挂多条别名**（0～N，可随时加）。专吃工艺确认表乱写 / 乱定的厂名。别名只用于解析与核对；下游列不存别名原文。创建时别名可空，对不上表头就回一览加别名，禁止因此把原文入库 |
| S14 | **核算不构成约束。** 零件核价 / 加工费 / 模具费 / 总成 / 引擎的 **calculate、ready、能否开算** 不调用 `require_enabled`，不因主数据未登记或已禁用拒绝核算。本文只管业务列 **新写入或改成非空** 的门禁，以及列表 / 导出 / 覆盖删除等 **读路径** |

钢价、冲次单价不按供应商写，不走本文。  
采购对象指定对方：**日后**走本文门禁（S12）。点选细则仍见 [bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md)；本文只锁 `require_enabled`，不把指定对方提前进本期。

冲压工厂不是基地、不是项目。同一家厂服务多座基地、多个项目 = **一行**，禁止按基地区成两条。

---

## 3. 位置

```
基地               ★ 位置绝对上游
供应商             ★ 对方绝对上游（与基地平行，互不隶属）
    │
    ├── 项目（只依赖基地；不依赖供应商）
    │
    └── stamping / bom / costing   写供应商字符串时先问本文
```

下游继续存字符串，值 = **全称**（规范名，与现网工艺确认一致）。表头乱写只用于核对；入库仍是主数据全称，不写缩写、不写 ERP、不写别名原文。列表可旁注缩写，覆盖键认全称。

引用保护（宪法 §4.3）：一期 **子表不声明** 指向本表的外键（采购对象设计已写明不是下一跳；工艺主表 / 年度价同样先存字符串）。父 Model **禁止** `relationship` / import 下游。拦改主键/删除的手段是 **产品不提供这两项**（S4 / S8 / S9），不是去 `count` 零件。

只按 `location` 写的路径（钢价、冲次单价）不过本文。  
按供应商 **写入** 的路径：先过本文（已启用）。**核算（calculate / ready）不过本文**（S14）。列表 / 导出等 **读** 路径可用 `expand_for_query`。

---

## 4. 切片与入口（落地时一次对齐）

| 项 | 定稿 |
|---|------|
| 切片 | `masterdata`（与基地、项目同一切片）。宪法 §4.1 上游 / 基础数据已含 `masterdata` |
| 代码 | `app/models/masterdata/supplier.py` · `routers/masterdata/supplier/` · `services/masterdata/supplier/` · `repositories/masterdata/supplier/` · `parsers/masterdata/supplier_parser.py`；前端 `static/js/features/masterdata/supplier/{upload,list}/` |
| 表 | `suppliers`（主键 `full_name`，`String(100)`，与年度价 `supplier_name` 同宽）· `supplier_aliases`（附属行）。凡存规范全称的业务列统一 `String(100)`，见 §5.6 |
| HTTP | `/api/masterdata/suppliers` **只给供应商两页**：列表 / 手工创建 / 改启用与别名 / **下载模板 / 上传 / 一览导出**。下游上传/计算/列表下拉**不另开**这套 HTTP：各切片沿用现有接口，Service 内调本切片。避免工艺上传权限绑 `menu:supplier-upload` |
| 前端 | 见本节 4.1～4.6。侧栏 **供应商** 是二级分组：叶子 **上传** + **一览表**（对齐项目 / 加减价政策）。供应商多，批量建档走上传，对账走导出 |

基地 / 项目 Model **禁止** `relationship` 指向供应商。供应商 Service **禁止** import 冲压 / BOM / 核价（S2）。下游 Service **可以**调 `SupplierService`。

---

### 4.1 侧栏位置

落地后，主数据分组在「项目」二级之后是 **二级分组「供应商」**（对齐项目：父级无页面，两片叶子）。不要把上传和一览合成一个 `#/supplier`，也不要另开一级侧栏分组：

```
仪表盘
冲压工程
焊接工程
一事一议
核价
文件溯源
主数据
  基地              ← 单叶
  项目              ← 二级分组（上传 / 一览表）
  供应商            ← 二级分组（上传 / 一览表）
设置
```

侧栏 HTML（插在项目 `</li>` 之后，仍在 `masterdataSubmenu` 内；嵌套 class 抄 `vehicleModelSubmenu`）：

```html
<li class="submenu-item has-submenu">
    <a href="javascript:void(0)" class="submenu-link" data-submenu-toggle="supplierSubmenu">
        <!-- 现网同款 outline SVG + 展开箭头，对齐项目 -->
        <span>供应商</span>
        <svg class="w-3.5 h-3.5 ms-auto submenu-arrow" …>…</svg>
    </a>
    <ul class="submenu submenu-nested" id="supplierSubmenu">
        <li>
            <a href="#/supplier-upload" class="submenu-link submenu-link-nested" data-page="supplier-upload">
                <span>上传</span>
            </a>
        </li>
        <li>
            <a href="#/supplier-list" class="submenu-link submenu-link-nested" data-page="supplier-list">
                <span>一览表</span>
            </a>
        </li>
    </ul>
</li>
```

父级**禁止** `data-page`。叶子必须 `data-page="supplier-upload"` / `data-page="supplier-list"`，与 `canAccessPage` → `menu:supplier-upload` / `menu:supplier-list` 对齐。`permissions.js` 的 `PAGE_MENU_CODE` **不必**加特例。

无对应 `menu:` 时藏叶子；两叶都无权限则空「供应商」分组一并隐藏。若「基地」「项目」「供应商」都空，空「主数据」一并隐藏。

落地时同步改：`static/index.html`、`docs/front-end.mdc`「侧栏顺序」与 §2.1 路由表、`features/index.js` 目录注释；[location-design.md](location-design.md) / [vehicle-model-design.md](vehicle-model-design.md) 里「供应商仍不建链」改为已建链。

兼容：`#/supplier` → `supplier-list`（与现网 `#/vehicle-model` → `vehicle-model-list` 同类）。

---

### 4.2 路由与 pageMeta

| 项 | 上传 | 一览表 |
|---|------|--------|
| Hash | `#/supplier-upload` | `#/supplier-list` |
| `pages` key | `supplier-upload` | `supplier-list` |
| 模块 | `static/js/features/masterdata/supplier/upload/` | `static/js/features/masterdata/supplier/list/` |
| 顶栏标题 | 供应商上传 | 供应商一览 |
| `en` | `SUPPLIER UPLOAD` | `SUPPLIER` |
| `breadcrumb` | `['主数据', '供应商', '上传']` | `['主数据', '供应商', '一览表']` |

`app.js`：`import` 两页 + `pages[...]`；递增相关 `?v=`。

`features/index.js`：

```javascript
'supplier-upload': {
    title: '供应商上传',
    en: 'SUPPLIER UPLOAD',
    breadcrumb: ['主数据', '供应商', '上传'],
},
'supplier-list': {
    title: '供应商一览',
    en: 'SUPPLIER',
    breadcrumb: ['主数据', '供应商', '一览表'],
},
```

直链无对应 `menu:` → 现网守卫：`fallbackPageName()` + Toast。不要单独做登录后默认进供应商页。

---

### 4.3 权限树位置

走 [permission-design.md](../permission-design.md) §0。插在 `menu:vehicle-model` **之后**、`menu:settings` **之前**。树形态对齐 `menu:vehicle-model`：**分组 + 上传叶 + 一览叶**。**不进** `defaults` / `mandatory`。

```
menu:masterdata                          # 已有
  ├── menu:location                      # 已有
  ├── menu:vehicle-model                 # 已有
  └── menu:supplier                      # 二级分组，label「供应商」，无页面
        ├── menu:supplier-upload         # 叶子，label「上传」
        │     ├── op:supplier-upload:view
        │     └── op:supplier-upload:upload
        └── menu:supplier-list           # 叶子，label「一览表」
              ├── op:supplier-list:view
              ├── op:supplier-list:export
              ├── op:supplier-list:create
              └── op:supplier-list:update
menu:settings
```

| 码 | 用途 |
|---|------|
| `menu:supplier` | 授权树分组、侧栏「供应商」；不是页 |
| `menu:supplier-upload` | 进上传页、侧栏「上传」 |
| `op:supplier-upload:view` | 看上传页；下载模板 |
| `op:supplier-upload:upload` | 提交 Excel |
| `menu:supplier-list` | 进一览表、侧栏「一览表」 |
| `op:supplier-list:view` | 列表 |
| `op:supplier-list:export` | 导出 Excel（列与导入模板相同） |
| `op:supplier-list:create` | 抽屉手工新增、新增别名 |
| `op:supplier-list:update` | 启用/禁用、改/删别名 |

**没有** `op:supplier-list:delete`（S8）。  
CRUD：上传路由绑 `upload` 叶权限；一览写操作绑 `list` 叶对应 `op`。按钮 `can('op:…')`，不能只藏侧栏。

---

### 4.4 上传页 UI

**参照** 项目上传 / 基准价格上传，不是把一览表和上传挤在同一页。供应商多，批量建档走本页，不要逼人在抽屉里一条条敲。

- 拖拽区 + 「选择文件」+ 「下载模板」；只选 `.xlsx` / `.xls`
- 主按钮红底 `#d32f2f`（本页只用这一种红）
- 同步上传，进度条即可；不走异步任务壳
- 成功 Toast 后可深链一览表，不在本页画数据表

模板列见 §5.4。整单事务：任一行失败则全部不写入。

---

### 4.4.1 一览表 UI

**参照** 基地页的**面板 + 表 + 抽屉 + 操作列**，走前端规范 §4.4.6（设置 / 简单 CRUD）。不要做成零件价格一览那种 HUD 密表，也不要做成项目一览那种按基地分卡（供应商不按基地分行）。

抄这些：

- 外框 `bg-[#121215] border border-[#2c2c2c]`；表头 `text-[10px]`，表体 `text-xs`
- 主按钮红底 `#d32f2f`（本页只用这一种红，不用 `#FF1E27`）
- 新增 / 编辑 / 启用禁用用 **抽屉**（z-index ≥ 80/85）；启用禁用先确认
- 操作只在操作列；**禁止**整行点击

不要抄这些：

- 拖拽上传区（在上传页）
- 项目那种 HUD 分卡
- **删除按钮**（S8）

| 区域 | 内容 |
|---|------|
| 顶 | 标题「供应商」；说明一句：全称是规范名、与现网工艺确认一致、给下游存；缩写只给人看；别名吸收表头乱写（一条可多条）。创建后三者不改。已启用才能新引入 |
| 主按钮 | 「导出 Excel」（`op:supplier-list:export`）+「新增供应商」（`op:supplier-list:create`）。**不放**上传按钮（上传在上传页） |
| 筛选 | 关键字一框：缩写 / 全称 / ERP 代码 / 别名包含匹配（供应商多，不要抄基地页「无搜索」）。可选状态胶囊：全部 / 已启用 / 已禁用。筛选在服务端，`GET` 带 `q=` / `is_enabled=` |
| 表列 | 缩写、全称、ERP 代码、别名、状态（启用/禁用）、操作 |
| 操作列 | 编辑（别名）、启用或禁用 |
| 新增 | 抽屉：缩写 + 全称 + ERP 代码必填；**别名可多条**（每行一个；strip、互斥校验见 §5.2）。工艺常见乱写建议创建时一并录入。默认已启用。主键已存在 → Toast「该全称已有供应商」 |
| 编辑 | 抽屉：缩写 / 全称 / ERP 代码只读；别名列表可继续追加 / 删除（S13：一条多条是预期） |
| 启用 / 禁用 | 确认抽屉后再 `PATCH is_enabled`。状态列克制钛灰字，不用绿色徽章 |

别名展示：同行逗号分隔。没有则 `—`。列表按 `sort_order`；第一期无排序控件。

**分页**：供应商多，一览走常规列表 `page` + `size`（`page-size.js`，默认 10）。`GET` → `ApiResponse[PageResult[SupplierVO]]`。导出**不分页**，与当前筛选同一套 `q` / `is_enabled`，一次全量。

点选展示「缩写（全称）」，如下拉 `常庆（安庆常庆汽车部件有限公司）`。**value 是全称**（规范名，与落库一致），不是缩写。

下游找不到时 Toast 带 `#/supplier-list`，**不要**在工艺/计算/采购对象页内嵌创建表单。

一览 **禁止** 再打工艺 / 年度价 HTTP 去拉 `DISTINCT` 当「待补清单」（S2 / S7）。落地对照现网厂名：人眼看工艺列表或年度价已有写法，写进上传模板的全称/别名列，或仓库外一次性打印脚本（只打印、不 insert）。

---

### 4.5 下游页：不改菜单位置

工艺上传、零件列表、加工费、零件核价、年度价、采购对象等**侧栏条目不动**。

控件文案：

| 页面 | 仍叫 | 同一实体 |
|---|---|---|
| 零件列表 / 加工费 / 零件核价 | **冲压工厂** | 本文 |
| 年度零件价 | **供应商** | 本文 |
| 采购对象 | **供应商**（合同对方） | 本文 |

选项改为各切片接口内读本文，废止自由输入与从本表 `DISTINCT` 当选项来源。**工艺确认上传无工厂下拉**，表头解析后 `require_enabled`。

仪表盘快捷入口**不**加「供应商」。

---

### 4.6 落地清单

**前端**

| 文件 | 动作 |
|------|------|
| `static/index.html` | 插入 §4.1 二级分组 |
| `static/js/features/index.js` | `pageMeta` 两页 + 目录注释 `masterdata/supplier/{upload,list}/` |
| `static/js/app.js` | 注册两页；兼容 `#/supplier` → `supplier-list` |
| `static/js/features/masterdata/supplier/upload/` | 上传模板 + 逻辑 |
| `static/js/features/masterdata/supplier/list/` | 一览模板 + 逻辑 |
| `static/js/features/stamping/process/upload/` | 工艺上传：不选手选冲压工厂；解析后门禁 |
| `app/common/permissions/catalog.json` | §4.3 树；再生成 `Perm.*` |
| `docs/permission-design.md` §7 可读树 | 同步 `menu:supplier*` |
| `docs/front-end.mdc` | 侧栏顺序、§2.1、features 目录 |

**后端（本切片 + 本期门禁触达）**

| 文件 / 位置 | 动作 |
|-------------|------|
| `app/models/masterdata/supplier.py` · Repository · Service · Router · Parser | 供应商 CRUD / 上传 / 导出 / 解析契约 |
| `app/database.py`（或迁移脚本） | §5.6 列宽 DDL |
| `app/common/upload_scope_validation.py` | 工艺 scope：厂名来自解析后 `require_enabled` 的规范全称（§6.0） |
| `app/services/stamping/upload/stamping_upload.py` | 解析后 `require_enabled`；落库规范全称；删除 `expand_for_query` |
| `app/routers/stamping/upload.py` | Form 只收 `file` |
| 各切片 `/filters`、列表 Repository（**列表 / 导出**，非 calculate） | `list_registered` / `list_enabled` + 查询 `expand_for_query` |

**交叉文档（与本文一并改，避免 implementer 只看一篇）**

| 文档 | 动作 |
|------|------|
| [stamping-process-confirmation-design.md](../stamping/stamping-process-confirmation-design.md) | §2 上传：不选手选工厂；解析后 `require_enabled`；落库全称；覆盖删除 `expand_for_query` |
| [vehicle-model-design.md](vehicle-model-design.md) §4.1 | 侧栏「供应商」二级分组（去掉「仍不建链」） |
| [location-design.md](location-design.md) 侧栏示意 | 供应商已建链 |
| [docs/README.md](../README.md) · [architecture.md](../architecture.md) | 状态改为「已落地（第一期）」 |
| [bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md) | 深链 `#/supplier-list`；落库规范全称（日后落地） |

---

## 5. 表结构

### 5.1 `suppliers`

| 列 | 说明 |
|---|------|
| `full_name` | 全称，**主键**，`String(100)`，创建后只读。本平台规范名。下游 `stamping_supplier` / `supplier_name` 存这个。例：安庆常庆汽车部件有限公司 |
| `abbreviation` | 缩写，唯一，`String(50)`，创建后只读。界面短名，例：常庆。**不**写入工艺列 |
| `erp_code` | ERP 代码，唯一，`String(50)`，创建后只读。对外身份，**不**写入工艺列 |
| `is_enabled` | 启用 / 禁用 |
| `sort_order` | 下拉与列表顺序。新建 = 当前最大 + 1。第一期不提供手改排序 |
| 审计 | `AuditUserMixin` |

布尔用 `is_enabled`。禁止逻辑删除 / 软删冒充 S8。禁止 `is_paused`、生效/失效年月。

缩写 ≠ 全称 ≠ ERP 代码；创建时三者都必须非空（strip 后）。不要只用其中一个当这一行。点选/落库用全称；下拉旁注缩写；对外对账用 ERP 代码。

主键选全称而不是缩写、不是 ERP 代码：现网工艺确认与 `stamping_supplier` 已经是全称；覆盖键、列表筛、核价结果行快照对齐规范全称，对齐基地用规范名当主键、当业务列。缩写只给人看。**禁止**把缩写或 ERP 代码写入 `stamping_supplier`。业务列宽度与 §5.6 对齐。**不要**把列改成整型 FK。

供应商 Model **禁止** `relationship` 指向冲压/BOM。别名同切片附属行，允许 `relationship` + `CASCADE`（`ondelete` / `onupdate` 都 `CASCADE`；宪法 §2.4 / §4.3）。

### 5.2 `supplier_aliases`

附属行，**不是**独立主数据。若日后删除供应商（本期不提供），别名随父 `ON DELETE CASCADE`。

**一条供应商 ↔ 多条别名**（S13）。工艺确认表「冲压承制公司」经常多字、少字、曾用名、带括号；这些全部作成别名，不要为此再建第二条供应商。

| 列 | 说明 |
|---|------|
| `alias` | 别名，主键，`String(100)`；全局唯一。例：常庆汽配、××（常庆）、少写「有限公司」的表头 |
| `full_name` | `ForeignKey("suppliers.full_name", ondelete="CASCADE", onupdate="CASCADE")` |

`alias` 与全称同宽：表头乱写可能接近正式名称长度。

创建时别名可空（0 条）。对不上工艺表头 → 来一览追加别名，**禁止**把未对上的原文当新供应商、也禁止把原文写入 `stamping_supplier`。

**同一解析命名空间**（SQLite 无法一条 UNIQUE 跨表，**Service 创建供应商和别名时四面都要查**）：

- 别名不得等于任一缩写、全称、ERP 代码
- 缩写 / 全称 / ERP 代码彼此不得相同，也不得等于任一条已有别名
- 别名彼此唯一（表上 `PRIMARY KEY`）；同一全称下多条别名互不相同
- strip 后非空

漏掉互斥会得到两行都能被 `resolve_canonical` 命中，无解。规范全称本身已在解析命名空间里，不必再把全称抄成别名。

### 5.3 种子

**无种子。** 不像基地有现网四字常量。空表是预期：工艺上传在未建行之前硬停，文案去一览表。

禁止 `ensure_seed_if_empty`。禁止 `scripts/backfill_suppliers` 一类从零件/年度价 `DISTINCT` 插入（S3 / S7）。现网厂名用**上传页 Excel** 一次灌进主数据（全称对上现网常见写法，其余写法放别名列），ERP 代码、缩写、全称都不准空着入库。

### 5.4 上传页模板

Parser 只被本切片 Service 调用。列（表头中文，第一行）：

| 列 | 必填 | 规则 |
|---|------|------|
| 缩写 | 是 | strip；非空；`String(50)` 内；不得等于已有全称 / ERP / 别名 |
| 全称 | 是 | strip；非空；`String(100)` 内 |
| ERP 代码 | 是 | strip；非空；`String(50)` 内 |
| 别名 | 否 | 同一格可多条（顿号 / 逗号 / 换行）。专吃工艺表头乱写。strip 后空段丢掉。互斥见 §5.2。全称不必再抄进本列 |

**不要**加「启用」列：新建默认已启用；改状态走一览抽屉。否则导出再导入会和「已有主键跳过、不覆盖」打架。

文件内去重与冲突：

- 同一全称、缩写 / ERP / 别名集合与首次出现相同 → 后行跳过（计入 `skipped_count`）
- 同一全称、缩写或 ERP 或别名集合不同 → **整单失败**（禁止猜哪一行）
- 文件内两行全称不同，但缩写或 ERP 或别名撞车 → **整单失败**
- 库里已有该全称 → 跳过、**不覆盖**缩写 / ERP / 别名 / 启用（改别名、改启用走编辑抽屉）
- 库里全称没有，但缩写或 ERP 或别名已被占用 → **整单失败**（禁止把别人的缩写/ERP 抢过来）

整单一个事务，任一行失败则全部回滚。抽屉 `POST` 遇到已有全称 → `BusinessException("该全称已有供应商")`，不要学 Excel 静默跳过。

`GET /api/masterdata/suppliers/template` → `StreamingResponse`（无 `ApiResponse`）。`POST /api/masterdata/suppliers/upload` 只收文件，返回 `ApiResponse[SupplierUploadResultVO]`（`created_count` / `skipped_count`，具名 VO）。同步即可，不走异步任务。

`GET /api/masterdata/suppliers/export` → `StreamingResponse`。列与模板完全相同（缩写、全称、ERP 代码、别名）；别名多个则顿号拼接，没有则空单元格。查询参数与一览筛选相同（可选 `q=` / `is_enabled=`），不传则全量。顺序与一览相同（`sort_order`）。不要加「状态」列，否则无法再导入。已有主键再导入仍跳过、不覆盖（改启用/别名走抽屉）。

`GET /api/masterdata/suppliers`：`page` + `size`（及可选 `q` / `is_enabled`）→ `ApiResponse[PageResult[SupplierVO]]`。  
`POST /api/masterdata/suppliers` 抽屉创建。  
`PATCH /api/masterdata/suppliers/{full_name}`：路径参数（中文全称须 URL 编码）；体只含 `is_enabled`（别名走子资源）。  
`POST` / `DELETE /api/masterdata/suppliers/{full_name}/aliases[/{alias}]`：增删别名。  
**没有** `DELETE` 供应商本体。

### 5.5 不做的表与入口

| 不做 | 原因 |
|---|------|
| 按基地拆行 | 同一厂服务多座基地仍是一行 |
| 供应商↔项目关系表 | 工艺覆盖键已经是基地+厂+项目+版本；不要第三张表 |
| 生效/失效、暂停 | S8 |
| 物理删除 API | S8 / S9 |
| 启动 / 脚本从下游灌入 | 批量走上传页 Excel，不要从零件表发明 |

### 5.6 业务列宽度（`String(100)`）

主键 `full_name` 最长 100。现网多处 `stamping_supplier` 仍为 `String(50)`，长全称会被 SQLite 截断；加宽**只扩列、不改历史值**（S10）。落地时一次 DDL，与供应商表同期：

| 表 / 列 | 现网 | 落地 |
|---------|------|------|
| `stamping_parts.stamping_supplier` | 50 | **100**（工艺主表，覆盖键） |
| `stamping_process_fees.stamping_supplier` | 50 | **100** |
| `stamping_process_fee_calc_logs.stamping_supplier` | 50 | **100** |
| `stamping_part_costs.stamping_supplier` | 50 | **100** |
| `stamping_part_cost_calc_logs.stamping_supplier` | 50 | **100** |
| `stamping_die_parts.stamping_supplier` | 50 | 100（布点上传仍写空；列宽对齐） |
| `stamping_die_fees.stamping_supplier` | 50 | **100**（快照来自工艺/布点，可能非空） |
| `stamping_die_fee_calc_logs.stamping_supplier` | 50 | **100** |
| `llm_analysis_reports.stamping_supplier` | 50 | **100**（筛选用，只读） |
| `bom_annual_part_prices.supplier_name` | 100 | 不动 |
| `upload_files.stamping_supplier`（文件溯源） | 100 | 不动 |

**不加 FK**（S9）。若某表历史上已被 50 截断，加宽后**禁止**批量回填。工艺上传门禁后的新行写规范全称；核算结果行快照随源工艺/费表字符串写入，**不过**本文 `require_enabled`（S14）。

别名 `supplier_aliases.alias` 已是 `String(100)`，与表头乱写同宽。

---

## 6. 解析契约（废止从文件发明身份）

查库、门禁、展开别名只发生在 **Service**（本切片或下游切片的 **写路径 / 读路径** 调本切片）。**禁止 Parser 调 Service / Repository**（宪法：Parser 只许 `app/common/` 纯函数）。**核算 orchestrator / ready 不调本文**（S14）。

供应商上传页：Service 调本切片 Parser 得到行，再互斥校验 / 插入。  
工艺上传：Parser 只抽出「冲压承制公司」字符串；Service 再 `require_enabled`。

规范化：输入 `strip`；空串不是供应商。不做全角转换、不发明未登记别名、不按拼音/包含关系模糊匹配。

| 方法 | 行为 |
|---|------|
| `resolve_canonical(raw)` | strip 后命中全称或缩写或 ERP 代码或别名 → **全称**；否则 `None` |
| `require_enabled(raw)` | 得到全称且 `is_enabled` → 返回全称。不存在 / 已禁用 → `BusinessException`，提示去一览表（可带 `#/supplier-list`）。**仅写路径用这个**（§6.0 表） |
| `expand_for_query(raw)` | 先 `resolve_canonical`；返回 `[全称, 缩写, ERP 代码] + 该行全部别名`（去重保序）。用于读历史业务行、覆盖删除、**列表/导出筛选** `IN (...)`。解析失败 → 空列表或由调用方当找不到。比基地多展开缩写/ERP，是为了极少数历史行误存短码时仍能筛到；**新写入仍只落全称**。**不**用于核算 calculate / ready 拦算（S14） |
| `list_enabled()` | 已启用，按 `sort_order`。采购指定 / 年度价等写路径下拉（工艺上传不用） |
| `list_registered()` | 全部已登记（含禁用），按 `sort_order`。列表筛选项 |
| `list_page(q, is_enabled, skip, limit)` | 一览表分页：关键字 + 可选状态；按 `sort_order` |

列表筛选项必须来自 `list_registered()`，**禁止**再 `DISTINCT` 业务表 `stamping_supplier` / `supplier_name` 当身份选项（S7）。用户选全称后，**查询条件**用 `expand_for_query`，才能命中历史乱写行。

**`list_enabled` / `list_registered` 分工**（对齐基地设计，禁止混用）：

| 场景 | 方法 | 说明 |
|------|------|------|
| 工艺上传（解析后门禁，不点选） | `require_enabled(表头)` | 命中全称 / 缩写 / ERP / 别名且已启用 |
| 采购指定 / 年度价编辑等 **写路径** 下拉 | `list_enabled()` | 只列已启用；展示「缩写（全称）」，`value = 全称` |
| 零件列表 / 加工费 / 零件核价 / 模具费等 **列表筛** 下拉 | `list_registered()` | 含禁用，便于查历史；`value = 全称` |
| 用户选中某厂后的 **Repository 条件** | `expand_for_query(选中全称)` | `stamping_supplier IN (...)` 或等价 OR |
| 页内 HUD「冲压工厂数」 | 本表 `COUNT(DISTINCT stamping_supplier)` | 统计**写法**种数，不是主数据行数（S10） |
| 签约报表「已指定厂」筛 | 该页聚合 DISTINCT | 不是 `list_registered` 全量（§8） |

对上主数据之后，同一厂的乱写全称与规范全称在 HUD 里仍可能计成两个，直到业务行自然被覆盖成规范全称——接受（S10）。

### 6.0 写门禁

下游 **新写入或改成非空** 供应商字符串，一律 `SupplierService.require_enabled`。找不到 / 已禁用 → `BusinessException`，深链 `#/supplier-list`，不代建。落库只写**规范全称**。

| 门禁 | 何时 | 落地 |
|---|---|---|
| `require_enabled` | 工艺确认表上传（表头厂名解析后准入） | **本期**（S11） |
| `require_enabled` | 采购对象行指定或改成非空对方 | **日后**（S12）。清空不跑；再生成带回历史全称不跑 |
| `require_enabled` | 年度价非空 `supplier_name`（Excel / 列表编辑） | 随年度价改点选一并接，不是供应商切片本期必做 |

**本期硬路径（工艺确认上传）：**

1. 表单**只选文件**。不选采购基地、不选项目、不选冲压工厂。  
2. Parser 只抽出「冲压承制公司」字符串（禁止 Parser 调 Service）。抽不出 → 整单失败，**不要**用空值或已选值顶替。  
3. `require_enabled(表头)`：未登记或已禁用 → 硬停，文案去一览表。返回规范全称（全称 / 缩写 / ERP / **任一条别名** 都算命中）。  
4. 落库 **`stamping_supplier` = 规范全称**（`require_enabled` 的返回值）。禁止写 Parser 原文、禁止写缩写、禁止写 ERP。覆盖删除 `stamping_supplier IN expand_for_query(规范全称)`。

**Scope：**

- **覆盖键 / 删除 / 落库** 的厂名 = 表头经 `require_enabled` 后的规范全称，**不是** Parser 原文。  
- `version` 仍从文件解析（§6.4）；`vehicle_model` 从文件解析后走项目 `require_introducible_by_code`（基地由项目行带出）。  
- `validate_stamping_process_upload_scope` 接收 **已门禁的全称** + 已门禁的项目代号 + Parser 的 `version`。厂名缺了在步骤 2 失败。

Router `POST /api/stamping/upload/` Form 只收 `file`。worker 解析后再跑项目 / 供应商门禁。布点上传**不加**供应商字段。工艺确认表设计须同步：[stamping-process-confirmation-design.md](../stamping/stamping-process-confirmation-design.md) §2。

**日后路径（采购对象改供应商）：** 仍走采购对象切片 PATCH，不新开供应商 HTTP。非空 body → 本切片 `require_enabled`，落规范全称；空串 = 清空，不跑门禁。禁用后不准新指定、不准改成该厂；行上已有全称仍可查。页面下拉 `list_enabled`（value = 全称），Toast 深链一览表。细则（确认/审核锁定、自制清空）归指定供应商设计，不得另写第二套「是不是合法厂名」。

不要包一层 `require_supplier` 分发器；点名 `require_enabled`。

### 6.1 写

门禁分层见 §6.0。落库只写**规范全称**。

工艺确认表：文件写「安庆常庆汽车部件有限公司」或「常庆汽配」：全称或任一别名命中则通过，**零件行仍落规范全称**（`安庆常庆汽车部件有限公司`）。同一家下一份文件换一种乱写：先在一览追加别名，再传；不要新建第二条供应商，也不要把缩写写进工艺列。

年度价 `supplier_name` 可空（现网常空）。空 = 不校验、不写。非空 → `require_enabled`，落规范全称。禁止再自由打字。

覆盖上传工艺（同基地 + 厂 + 项目 + 版本整包替换）：删除范围必须 `stamping_supplier IN expand_for_query(规范全称)`，不要只删规范全称这一档，否则历史乱写包会残留，变成两套身份。

### 6.2 读

**不改写**已有业务表里的乱写全称。列表 / 导出 / 覆盖删除前的查询用 `expand_for_query`。

已禁用：不准 **写路径** 新引入；已有结果仍可查、筛选里用 `list_registered()`。

### 6.2.1 核算不构成约束（S14）

**零件核价、加工费、模具费、总成核价、核价引擎** 的 `calculate` / `ready` / 能否开算：**不**调用 `require_enabled`，**不**因供应商未登记或已禁用而拒绝核算。核算只消费工艺库 / 结果表里**已有**的 `stamping_supplier` 字符串；结果快照随源行写入，不过本文门禁。

列表页筛「冲压工厂」、导出收窄：`list_registered` + `expand_for_query` 属于 **读路径**，不是算前门禁。总成「每家厂是否算完」、零件价锁 `全部工厂` 等纪律归各 **costing** 设计，**不在本文定义**。

### 6.3 禁用 / 不删除 / 不改主键

| 动作 | 行为 |
|---|------|
| 禁用 | `UPDATE is_enabled`。已有工艺 / 年度价 / 采购对象行不改 |
| 改缩写 / 全称 / ERP 代码 | 产品不提供（S4） |
| 删除 | 产品不提供（S8）。不要做 DELETE 路由，不要用禁用文案冒充删除 |

没有业务列外键，删除会成功删掉主数据而留下孤儿字符串——所以不准删（S9）。这与基地 B8「第一期没有项目表时删除会成功」不同：本文从一开始就选择不删。

### 6.4 工艺覆盖键

现网唯一键仍是：基地 + 冲压厂 + 项目 + 版本 + 零件号。冲压厂列继续存**全称**（规范全称），键结构不变。上传门禁见 §6.0。版本仍从文件解析。

---

## 7. 找不到 / 引擎

| 情况 | 去哪 |
|---|------|
| 字符串对不上缩写、全称、ERP 代码或别名 | 一览表给已有行追加别名，或新建（三者必填）后把乱写放别名 |
| 有行但已禁用 | 一览表改为启用；下游不代建 |
| 工艺表头厂名对不上任何全称 / 缩写 / ERP / 别名 | 不准传；去一览新建或给已有行加别名。**禁止**把表头原文写入 `stamping_supplier` |

上传/计算/采购对象页可深链 `#/supplier-list`，不得内嵌创建。

引擎入口仍是 **基地 + 年 + 月**，不过本文。第二步项目名单见项目设计。

**核算不过本文（S14）：** 零件核价 / 加工费 / 模具费 / 总成 **calculate 与 ready** 不因主数据拦算；细则见各 costing 设计。成品核价 **不认** `stamping_supplier`（现网已定），本文不改那条。

---

## 8. 谁改读本文 / 谁不要动

**要改（本期：写门禁、筛选项、列宽）：**

- **工艺确认上传（必做门禁）：** 表单不选冲压工厂；解析后 `require_enabled`（乱写靠多条别名）；覆盖删除 `expand_for_query`；**落库只写规范全称**；改 `upload_scope_validation` 与 `StampingUploadService`（§6.0）。同步 [stamping-process-confirmation-design.md](../stamping/stamping-process-confirmation-design.md)
- **§5.6 列宽：** 凡存 `stamping_supplier` 的业务列扩到 `String(100)`（不只 `stamping_parts`）
- 零件列表 / 加工费列表 / 零件核价**结果列表**：**筛选项** `list_registered()`；**查询** `expand_for_query`；HUD 工厂数仍本表 DISTINCT（读路径，不是算前门禁）
- 文件溯源：工艺上传门禁后写入规范全称；历史乱写不改写。不加供应商外键
- LLM：只读本表 Model（解释层隔离，**禁止**调 SupplierService）。现网库里的乱写要对上就在一览表加别名，不要在 LLM 里保留第二套厂名地图
- 各切片 `/filters` 冲压工厂（**列表 / 导出**）：`list_registered` + 查询 `expand_for_query`；`value = 全称`；禁止业务表 `DISTINCT` 当身份选项。采购指定 / 年度价等 **写路径** 下拉仍用 `list_enabled`

**日后（同一门禁，不在本期供应商落地范围）：**

- 采购对象指定 / 改供应商：PATCH 非空 → `require_enabled`（S12）。见 [bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md)
- 年度零件价：Excel / 列表编辑非空则 `require_enabled`，落规范全称；空仍允许。下拉 `list_enabled`

**不要改（第一期）：**

- 钢价、冲次单价、废料月度销售价（无供应商维度）
- 模具布点 / 模具单价 / 检具费（不认供应商；APQP）
- 模具费计算锁仍是年 + 基地 + 项目；附加筛「空=全部」可留，新布点供应商为空是预期
- 成品核价不认冲压工厂
- **核算不构成约束（S14）：** 零件核价 / 加工费 / 模具费 / 总成 / 引擎的 calculate、ready **不接** `require_enabled`；不因主数据未登记或已禁用拦算
- 给业务列加供应商 **FK**（S9）；间接下游（结果表、日志、溯源）同样不加
- 全库历史行批量改写成规范全称（S10）
- 钢厂 / `material_mill` 收进本文
- 供应商切片 `count` 下游 / import 冲压·BOM
- 签约报表下拉：现网「当前清单已指定去重」是该页聚合，不是主数据目录；落地后指定值已是规范全称，不必改成 `list_registered` 全量（未指定的厂不应出现在合同附件筛里）

---

## 9. 范围

**做：** 切片 `masterdata` 供应商（侧栏二级：上传 + 一览表；抽屉手工增加 + Excel 上传 / 导出；缩写 + 全称 + ERP 代码 + 启用/禁用 + **一条多条别名** + `sort_order`）；一览分页 + 关键字筛选；§4.1～4.6；**工艺确认上传写门禁（§6.0 / S11）**；**§5.6 列宽**；写路径门禁 + 列表/导出读路径（§6）；**核算不过本文（S14）**；新写入规范全称；历史乱写保留（S10）。  
**锁给日后：** 采购对象改供应商（S12）；年度价非空 `supplier_name` 门禁 + 点选（§6.0 表）。

**不做：** 本期做采购对象指定页；把工艺表头原文或缩写写入 `stamping_supplier`；为每一种乱写新建一条供应商；启动或脚本从下游表灌入种子；钢厂主数据；一件对多家；合同号/单价；按基地区分同一供应商成两条；全库整型外键；业务列 FK；改缩写 / 全称 / ERP 代码；物理删除；生效/失效日期；暂停；逻辑删除；手改 `sort_order`；Excel 带启用列；异步任务壳（同步即可）；一览表再打下游 HTTP 当待补清单；工艺页内嵌创建；布点认供应商；成品核价改认工厂；全库批量把历史乱写改写成规范全称；**在核算 calculate / ready 接 require_enabled 或拦算**（S14）。

侧栏「供应商」与「基地」「项目」分开展示，不要做成同一张表。

---

## 10. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-08 | 定稿：全称主键；缩写 / ERP；启用禁用；别名 0～N；工艺上传门禁 S11；采购 S12 锁日后；落库规范全称（非缩写） |
| 2026-09-08 | 补 §5.6 业务列宽清单；§6 `list_enabled` / `list_registered` 分工；scope 与 `upload_scope_validation` 变更；§4.6 后端与交叉文档落地清单 |
| 2026-09-08 | 纠正：零件核价按 **基地+项目** 一趟算（锁 `全部工厂`），非按冲压工厂分趟 |
| 2026-09-08 | **S14**：核算 calculate / ready 不过本文；去掉开算前 require_enabled、总成 readiness 归 costing 设计 |
| 2026-09-08 | 工艺上传改为解析后门禁：不选手选工厂；`require_enabled(表头)`；落库规范全称 |
| 2026-09-08 | 清熵：去掉供应商 `assert_matches_selected`、`list_enabled_options` / `SupplierOptionVO`、cascade `enabled_suppliers`（工艺页不再选手选工厂） |
| 2026-09-08 | 下游页表：工艺上传不再与列表页共用「冲压工厂」控件行 |
