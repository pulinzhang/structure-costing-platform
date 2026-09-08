# 基地 — 设计定稿

> 状态：**已落地**  
> 界面：**基地**（上传页「采购基地」为同一实体）。库字段：`location`。  
> 项目见 [vehicle-model-design.md](vehicle-model-design.md)。本文不定义项目。  
> 引用保护见架构宪法 **§4.3**（谁引用谁负责；修改与删除同时支持）。

---

## 0. 一句话

> **基地是业务绝对上游。有没有这座基地、现在能不能按基地写入，只认本文。下游找不到：停止，来基地页手工增加。**

---

## 1. 为什么做

现网基地不是实体，是常量和各表上的 `location` 字符串。新基地要改代码；钢价、冲次单价只按基地写，却没有「这座基地还在不在」的裁决。项目必须挂在基地上，所以基地必须先成立，并且是绝对上游。

---

## 2. 已定规则

| # | 规则 |
|---|------|
| B1 | **绝对上游。** 不依赖项目、冲压、BOM、一事一议、核价。项目设计依赖本文，本文不依赖项目设计 |
| B2 | 只在基地页手工增加。下游找不到就回本页手工补，禁止代建、禁止 `get_or_create` |
| B3 | 凡选**采购基地**，选项只来自本文。废止 `PROCUREMENT_LOCATIONS` 与前端写死的四基地数组。**废料价矩阵不是本文**（见 §8） |
| B4 | **启用 / 禁用** 即可。已启用才允许新引入。不做生效日期、失效日期、暂停 |
| B5 | 规范名创建后不改。历史「×基地」用别名，引入新数据只写规范名。废止 `location_candidates` |
| B6 | **修改与删除同时支持。** 启用/禁用是改非主键，外键不管。删除只 `DELETE` 自己。拦改主键/删除的是数据库（子表 `ON UPDATE RESTRICT` + `ON DELETE RESTRICT`），不是基地去点名项目。删除文案：**「仍被引用，不能删除」**。规范名创建后不改（B5）；子表仍必须同时声明 `onupdate="RESTRICT"`，禁止只拦删除 |
| B7 | 不从下游表 `DISTINCT location` 发明自己 |
| B8 | **可先于项目落地。** 项目表出现后，由项目声明外键，B6 才有直接下游。第一期没有项目表时，删除会成功——这是预期，不是漏洞 |

规范名与现网一致：`大连`、`芜湖`、`鄂尔多斯`、`青岛`。  
冲压工厂不是基地，见 [supplier-design.md](supplier-design.md)。

本文只回答：这个 `location` 是不是已登记基地、**现在**能不能按基地写入。  
按项目写、引擎里有哪些项目，见项目设计。

---

## 3. 位置

```
本文 基地          ★ 绝对上游（切片 masterdata）
    │
    ▼
项目               没有基地行不能建项目；项目表声明 FK（落地项目时加）
    │
    ▼
stamping / bom / yishiyiyi / costing / dashboard / llm
```

只按 `location` 写的路径（**基价**、钢材联动结果、冲次单价）只过本文。  
按 `(location, vehicle_model)` 写的路径：先过本文，再过项目设计。  
**基准价格**（`steel_base_prices`）有 `location`：新写入 `require_enabled` 只落规范名；列表/核价读历史用 `expand_for_query`。不改写已有行，不加基地外键（不是下一跳）。  
**厚度加减价政策没有 `location` 列**（键是年 + 月 + 钢厂 + 大类），不过本文、不加基地外键。核价：基地只用来取该基地基价；加减价按钢厂 + 大类命中政策，见 [thickness-policy-category-level-design.md](../yishiyiyi/thickness-policy-category-level-design.md)。

下游继续存字符串 `location` = **规范名**（新写入）。历史行可能仍是别名，读时用 §6.2 展开，**不改写历史业务行**。零件/钢价的 `location` 列不是基地的下一跳，不加基地外键（宪法 §4.3）。

---

## 4. 切片与入口（落地时一次对齐）

| 项 | 定稿 |
|---|------|
| 切片 | `masterdata`（文档已在 `docs/masterdata/`）。落地时写入宪法 §4.1 **上游 / 基础数据** |
| 代码 | `app/models/masterdata/` · `routers` · `services` · `repositories`；前端 `static/js/features/masterdata/location/` |
| 表 | `locations`（主键 `location`，`String(50)`，与现网业务列同宽）· `location_aliases`（附属行） |
| HTTP | `/api/masterdata/locations` **只给基地页 CRUD**。上传/计算/列表下拉**不另开**这套 HTTP：各切片沿用现有接口，Service 内调本切片（与牌号分类「核算不另做一套 API」相同）。避免上传权限绑 `menu:location` |
| 前端 | 见本节 4.1～4.6 |

---

### 4.1 侧栏位置

现网顺序见前端规范。落地后改为：

```
仪表盘
冲压工程
焊接工程
一事一议
核价
文件溯源
主数据          ← 一级分组；在设置之上
  基地          ← 单叶
  项目          ← 二级分组（上传 / 一览表），见 [vehicle-model-design.md](vehicle-model-design.md)
  供应商        ← 二级分组（上传 / 一览表），见 [supplier-design.md](supplier-design.md)
设置
```

**主数据**放在设置正上方：维护基地不是日常上传/核算路径，菜单按使用频率靠后。业务上仍是绝对上游（§3），**不要**并进「设置」（用户/系统配置与基地不是一类）。也不进一事一议。  
分组本身**没有页面**（对齐「冲压工程」：`javascript:void(0)` + `data-submenu-toggle`，**不要**学「设置」把父级链到某 hash）。

子菜单：基地为单叶；项目为二级分组（上传 + 一览表）；供应商为二级分组（上传 + 一览表），见 [supplier-design.md](supplier-design.md)。

无 `menu:location` / 项目两叶均无权限时，`applySidebarPermissions` 会藏叶子，空分组一并隐藏。

落地时同步改：`static/index.html`、`docs/front-end.mdc`「侧栏顺序」与 §2.1 路由表、`features/index.js` 目录注释。

侧栏 HTML 形态（插在「文件溯源」`</li>` 与「设置」之间）：

```html
<li class="sidebar-nav-item has-submenu">
    <a href="javascript:void(0)" class="sidebar-nav-link" data-submenu-toggle="masterdataSubmenu">
        <!-- 现网同款 outline SVG，不新增 style.css class -->
        <span>主数据</span>
        <svg class="w-3.5 h-3.5 ms-auto submenu-arrow" …>…</svg>
    </a>
    <ul class="submenu" id="masterdataSubmenu">
        <li>
            <a href="#/location" class="submenu-link" data-page="location">
                <span>基地</span>
            </a>
        </li>
    </ul>
</li>
```

项目二级分组（上传 / 一览表）HTML 见 [vehicle-model-design.md](vehicle-model-design.md) §4.1，插在「基地」`</li>` 之后。

父级**禁止** `data-page`（否则会被当成可进页面）。叶子必须 `data-page="location"`，与 `canAccessPage('location')` → `menu:location` 对齐。`permissions.js` 的 `PAGE_MENU_CODE` **不必**为 `location` 加特例。

### 4.2 路由与 pageMeta

| 项 | 定稿 |
|---|------|
| Hash | `#/location` |
| `pages` key | `location` |
| 模块 | `static/js/features/masterdata/location/`（`template.js` + `index.js` → `pageConfig`） |
| `app.js` | `import` + `pages.location`；递增相关 `?v=` |
| 顶栏标题 | 基地 |
| `en` | `LOCATION` |
| `breadcrumb` | `['主数据', '基地']` → `STAMPING // 主数据 // 基地` |

`features/index.js`：

```javascript
location: {
    title: '基地',
    en: 'LOCATION',
    breadcrumb: ['主数据', '基地'],
},
```

直链无 `menu:location` → 现网守卫：`fallbackPageName()` + Toast。不要单独做登录后默认进基地。

### 4.3 权限树位置

走 [permission-design.md](../permission-design.md) §0。`catalog.json` 的 `tree` 里插在 `menu:file-trace` **之后**、`menu:settings` **之前**（与侧栏同序）。**不进** `defaults` / `mandatory`。

```
menu:file-trace
menu:masterdata                          # 分组，可勾，label「主数据」
  └── menu:location                      # 叶子，label「基地」
        ├── op:location:view
        ├── op:location:create           # 新增基地、新增别名
        ├── op:location:update           # 启用/禁用、改/删别名
        └── op:location:delete           # 删除基地
menu:settings
```

| 码 | 用途 |
|---|------|
| `menu:masterdata` | 授权树分组；侧栏分组不是页 |
| `menu:location` | 进基地页、侧栏「基地」 |
| `op:location:view` | 列表 |
| `op:location:create` | 新增基地 / 别名 |
| `op:location:update` | 启用/禁用、改别名 |
| `op:location:delete` | 删除基地 |

第一期不做 `op:location:export`。  
CRUD 路由：`view` 看，写操作对应该 `op`。按钮 `can('op:location:…')`，不能只藏侧栏。

### 4.4 本页 UI

**参照** `static/js/features/settings/users/template.js`（用户管理）的**面板 + 表 + 抽屉 + 操作列**，走前端规范 §4.4.6（设置 / 简单 CRUD）。不要做成零件价格一览 / 牌号分类那种 HUD 密表。

抄这些：

- 外框 `bg-[#121215] border border-[#2c2c2c]`；表头 `text-[10px]`，表体 `text-xs`
- 主按钮红底 `#d32f2f`（本页只用这一种红，不用 `#FF1E27`）
- 新增 / 编辑 / 启用禁用 / 删除用 **抽屉**（z-index ≥ 80/85）；启用禁用与删除先确认
- 操作只在操作列；**禁止**整行点击

不要抄这些（用户多、基地少）：

- 顶上三块 KPI（总用户 / 启用 / 管理员）
- 搜索框、状态筛选、「查询」按钮
- **分页**（数量少，一次列出全部；不用 `page-size.js`，列表 API 也不用 `page` / `size`）
- 授权树、改密码等用户专用抽屉

| 区域 | 内容 |
|---|------|
| 顶 | 标题「基地」；说明一句：规范名与别名一次录入；创建后规范名不改；已启用才能当采购基地写入 |
| 主按钮 | 「新增基地」（`op:location:create`） |
| 表列 | 规范名、别名、状态（启用/禁用）、操作 |
| 操作列 | 编辑、启用或禁用、删除 |
| 新增 | 抽屉：规范名 + 别名一次录入。别名至少一条、可多条（每行一个；strip、互斥校验见 §5.2）；默认已启用 |
| 编辑 | 抽屉：规范名只读；别名列表 + 添加/删除。一座基地可挂多条别名 |
| 启用 / 禁用 | 确认抽屉后再 `PATCH is_enabled`。状态列克制钛灰字，不用绿色徽章 |
| 删除 | 确认后 DELETE；失败 Toast「仍被引用，不能删除」 |

别名展示：同行逗号分隔（如 `青岛基地`）。创建后若删光则 `—`。列表按 `sort_order`；第一期无排序控件。**不分页**：GET 列表返回 `ApiResponse[list[…]]`，一次全部。

深链只有 `#/location`。找不到时 Toast 带这句话即可，**不要**在上传/计算页内嵌创建表单。

### 4.5 下游页：不改菜单位置

布点、冲次、钢价、BOM 等**侧栏条目不动**。这些页控件文案继续叫 **采购基地**（与「基地」同一实体），选项改为各切片接口内读本文，废止写死四字。**工艺确认上传不选手选基地**，规范名由项目主数据行带出。

仪表盘快捷入口**不**加「基地」（主数据不是核算看板）。

### 4.6 落地清单（前端）

| 文件 | 动作 |
|---|------|
| `static/index.html` | 插入 §4.1 分组 |
| `static/js/features/index.js` | `pageMeta.location` + 目录注释 `masterdata/location/` |
| `static/js/app.js` | 注册页面 |
| `static/js/features/masterdata/location/` | 模板 + 逻辑 |
| `app/common/permissions/catalog.json` | §4.3 树；再生成 `Perm.*` |
| `docs/permission-design.md` §7 可读树 | 同步 `menu:masterdata` |
| `docs/front-end.mdc` | 侧栏顺序、§2.1、features 目录 |

---

## 5. 表结构

### 5.1 `locations`

| 列 | 说明 |
|---|------|
| `location` | 规范名，**主键**，`String(50)`，创建后只读。业务表继续存这个字符串，不做全库整型 FK |
| `is_enabled` | 启用 / 禁用 |
| `sort_order` | 下拉与列表顺序。种子 1–4；新建 = 当前最大 + 1。第一期不提供手改排序 |
| 审计 | `AuditUserMixin` |

布尔用 `is_enabled`。禁止逻辑删除 / 软删冒充 B6。

### 5.2 `location_aliases`

附属行，**不是**独立主数据。删基地时 `ON DELETE CASCADE`。

| 列 | 说明 |
|---|------|
| `alias` | 别名，主键，`String(50)`；全局唯一 |
| `location` | `ForeignKey("locations.location", ondelete="CASCADE", onupdate="CASCADE")` |

**同一解析命名空间**（两表之间 SQLite 无法一条 UNIQUE 跨表，**Service 创建基地和别名时双向都要查**）：

- 别名不得等于任一规范名；规范名不得等于任一条已有别名
- 别名彼此唯一（表上 `PRIMARY KEY` / `UNIQUE`）
- strip 后非空

漏掉「规范名不得等于已有别名」会得到两行都叫 `青岛基地`（一座真基地 + 一条指向青岛的别名），`resolve_canonical` 无解。

基地 Model **禁止** `relationship` 指向项目。别名同切片附属行，允许 `relationship` + `CASCADE`（`ondelete` / `onupdate` 都 `CASCADE`；宪法 §2.4 / §4.3）。

### 5.3 种子

按现网 `PROCUREMENT_LOCATIONS` 顺序灌入，全部 **已启用**：

| `sort_order` | `location` | 种子别名 |
|---|---|---|
| 1 | 大连 | 大连基地 |
| 2 | 芜湖 | 芜湖基地 |
| 3 | 鄂尔多斯 | 鄂尔多斯基地 |
| 4 | 青岛 | 青岛基地 |

新基地**不**自动生成「×基地」后缀。创建时用户自己填别名（至少一条）；事后要兼容更多历史写法，在编辑抽屉里加。

---

## 6. 解析契约（废止 `location_candidates`）

查库、门禁、展开别名只发生在 **Service**（本切片或下游切片调本切片）。**禁止 Parser 调 Service / Repository**（宪法：Parser 只许 `app/common/` 纯函数）。上传 Service 先 `require_enabled` / `expand_for_query`，把规范名和别名列表传给 Parser，Parser 只做字符串比对。

规范化：输入 `strip`；空串不是基地。不做全角转换、不发明未登记别名。

| 方法 | 行为 |
|---|------|
| `resolve_canonical(raw)` | strip 后命中规范名或别名 → 规范名；否则 `None` |
| `require_enabled(raw)` | 得到规范名且 `is_enabled` → 返回规范名。不存在 / 已禁用 → `BusinessException`，提示去基地页（可带 `#/location`）。**写入和新计算入口用这个** |
| `expand_for_query(raw)` | 先 `resolve_canonical`；返回 `[规范名] + 该行全部别名`（去重保序）。用于读历史业务行。解析失败 → 空列表或由调用方当找不到 |
| `list_enabled()` | 已启用，按 `sort_order`。上传 / 计算 / 引擎下拉 |
| `list_registered()` | 全部已登记（含禁用），按 `sort_order`。列表筛选项 |

列表筛选项必须来自 `list_registered()`，**禁止**再 `DISTINCT` 业务表 `location`（否则「青岛基地」会变成第二个选项，违背 B7）。用户选规范名后，**查询条件**用 `expand_for_query`，才能命中历史别名行。

### 6.1 写

新引入、新计算、引擎 `start_run`：用户选的或文件对上的字符串必须 `require_enabled`。落库只写**规范名**。文件里写「青岛基地」、已选「青岛」：别名命中同一规范名则通过，仍落 `青岛`。

### 6.2 读

**不改写**已有业务表里的 `青岛基地` 等历史值。查询用 `expand_for_query`，等价替换现网 `location_candidates`，但展开列表来自主数据，不是猜后缀。

已禁用：不准新引入、不准当引擎入口；已有结果仍可查、筛选里用 `list_registered()`。

### 6.3 删除 / 修改 / 禁用

| 动作 | 行为 |
|---|------|
| 禁用 | `UPDATE is_enabled`。外键不管。已有项目行不改 |
| 删除 | 只 `DELETE` 基地行（别名 `ON DELETE CASCADE`）。仍被独立子表引用 → `IntegrityError` → `BusinessException("仍被引用，不能删除")`。**禁止**文案点名项目，禁止基地切片 `count` 项目 / import 项目 |
| 项目落地后 | 项目 Model：`ForeignKey("locations.location", ondelete="RESTRICT", onupdate="RESTRICT")`。只改项目表，基地修改/删除代码不变。`onupdate` 与 `ondelete` 必须同时声明（宪法 §4.3）；产品不提供改规范名（B5），外键仍不得省略 `onupdate` |

B8 与宪法「不加外键则不准提供改主键、不准提供删除」不冲突：那句针对**永久拒绝**给直接下游加 FK。第一期是直接下游表还不存在；冲压/钢价等业务列按 §4.3 **本来就不是**直接下游，不挡删除。不是用禁用代替外键。有外键后修改（启用/禁用）与删除必须同时提供。

---

## 7. 找不到 / 引擎

| 情况 | 去哪 |
|---|------|
| 字符串对不上规范名或别名 | 本页手工增加基地或别名 |
| 有行但已禁用 | 本页改为启用；下游不代建 |

引擎入口仍是 **基地 + 年 + 月**。本文只卡：`require_enabled`。不过则硬停。第二步哪些项目见项目设计。

---

## 8. 谁改读本文 / 谁不要动

**要改（采购基地选项与写门禁）：**

- 废止 `app/common/procurement_locations.py`
- 废止 `location_candidates`（`stamping_part_cost/helpers.py` 及引擎 / 零件核价 / 导出引用）
- 前端写死 `['大连', '芜湖', '鄂尔多斯', '青岛']` 的列表筛选与 `<option>`
- 各切片 `/filters/locations`（及仪表盘范围选项）：改为调 `list_enabled` / `list_registered`，查询带 `expand_for_query`
- 布点 / 检具 / 冲次单价 / BOM 上传与列表（选手选基地后 `require_enabled`）、一事一议**基价**（上传表头经别名收成规范名再 `require_enabled`；筛选用 `expand_for_query`）、钢材联动与零件核价计算、核价引擎门禁。工艺确认上传不选手选，落库基地仍是项目行上的规范名
- 采购对象生成 / 列表 / 导出：见 [bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md)（生成 `require_enabled`；列表筛 `list_registered` + 查询 `expand_for_query`；清单头不加基地外键）
- LLM：只读本表 Model（解释层隔离，**禁止**调 LocationService）。现网写死的「青岛厂 / 芜湖厂 / 大连厂」**不进种子**；要对上就在基地页加别名，不要在 LLM 里保留第二套地图

**不要改（第一期）：**

- **废料月度销售价**矩阵仍用 `SCRAP_PRICE_LOCATIONS`（芜湖 / 大连 / 鄂尔多斯 / 青岛 / **福州** / **铝板**）。后两行不是采购基地，不能整表换成基地主数据。第一期废料写入**不过** `require_enabled`（已禁用的「青岛」仍能录废料价，是刻意范围，不是门禁漏洞）
- **基准价格**（`steel_base_prices`）：有 `location`，但不改写历史行、不加基地外键。现库已是规范名（大连 / 芜湖 / 鄂尔多斯 / 青岛）。若再出现「×基地」，只靠读路径展开，禁止批量改写成规范名
- **厚度加减价政策**（`steel_price_policies`）：无 `location` 列，上传只选年+月，不选手选基地。历史也没有基地可规范。核价按钢厂+大类命中，不按基地筛政策。清表重导见分类级厚度政策设计，本文不改写、不加基地外键、不 `require_enabled`
- 给 `stamping_parts.location`、钢价.location 加**基地**外键（宪法 §4.3：间接下游，不是直接下一跳。基地的直接下一跳是项目表）
- 全库历史行批量改写成规范名（读路径仍 `expand_for_query`）

---

## 9. 范围

**做：** 切片 `masterdata` 基地 CRUD（启用/禁用、别名、`sort_order` 种子）；种子四基地 + 四条「×基地」别名；侧栏「主数据 / 基地」（§4.1～4.6）；下拉改读本文；写路径 `require_enabled`；读路径 `expand_for_query`；引擎先过本文；废止常量和 `location_candidates`。

**不做：** 项目表；供应商表；政策；改规范名；自动建基地；自动生成新基地的「×基地」别名；全库整型外键；业务列 FK；生效/失效日期；暂停；逻辑删除；废料矩阵收进本文；手改 `sort_order`；导出；分页。

侧栏「基地」与「项目」分开展示，不要做成同一张表。
