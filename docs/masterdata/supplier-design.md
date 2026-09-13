# 供应商 — 设计定稿

> 状态：**第一期已落地**；**第二期已落地**。  
> 界面：**供应商**。工艺筛选项「冲压工厂」、采购对象「合同对方」、年度价「供应商」为同一主数据，不另立工厂表。  
> 库字段（现网下游仍存字符串）：`stamping_supplier` / `supplier_name`。工艺与采购对象 **新写入全称**。年度价是核算档案，**不设写门禁**（S15）。  
> 基地见 [location-design.md](location-design.md)，项目见 [vehicle-model-design.md](vehicle-model-design.md)。本文不定义基地、项目。  
> 引用保护见架构宪法 **§4.3**（谁引用谁负责；**修改与删除同时支持**）。直接下一跳：**工艺确认表** `stamping_parts`、**采购对象表** `bom_procurement_objects`（对方可空）。

---

## 0. 一句话

> **供应商只在供应商下增加：上传页 Excel，或一览表抽屉手工填。有缩写、全称、ERP 代码，以及启用/禁用。一条可挂多条别名，用来吃工艺确认表里乱写的厂名。写门禁：工艺确认、采购对象找不到就停止，来一览表或上传页补。禁止从工艺文件 / 年度价 / 采购对象发明供应商。工艺与采购对象落库只写规范全称。采购对象对方可空。直接下一跳外键 `RESTRICT`：改主键 / 删除只动自己，仍被引用则引擎拒绝。年度价只是报价档案：Excel 不门禁；列表手工编辑改下拉，可空。**

---

## 0.1 分期

| 期 | 状态 | 做什么 |
|---|------|--------|
| **第一期** | **已落地** | 供应商切片（上传 + 一览 + 别名 + 启用禁用）；工艺确认上传写门禁（S11）；`stamping_supplier` 列宽 100；列表 / 导出筛 `list_registered` + `expand_for_query`。现网厂名已在基础资料手工建档，**不是**从下游 `DISTINCT` 灌入 |
| **第二期** | **已落地** | **采购对象**行上指定 / 改合同对方：点选 + `require_enabled`（S12），**可空**。直接下一跳 `RESTRICT`：`stamping_parts.stamping_supplier`、`bom_procurement_objects.supplier_name`。一览提供 **改主键 / 改缩写与 ERP / 删除**。细则见采购对象指定设计 |
| **第二期附带** | **已落地** | **年度价列表**手工编辑：供应商从自由文本改为下拉（可空）。**不是**写门禁，**不是**下一跳（不加 FK），见 S15 |
| **更后** | 不在第二期 | 间接下游 FK（加工费 / 核价结果 / 年度价 / 溯源 / LLM）、签约报表本身、核算拦算 |

侧栏、Hash、供应商 HTTP **前缀** 第一期已定，第二期不改入口形态。第二期要改的是：采购对象读写、年度价列表下拉、下一跳 FK、一览改主键 / 删除、补 `op:supplier-list:delete`。

---

## 1. 为什么做

现网曾没有供应商实体。工艺确认表「冲压承制公司」**写的就是全称**，现网 `stamping_supplier` 也按全称入库。各文件仍会乱写（多字、少字、曾用名、带括号），但规范形态是全称，不是缩写。采购对象行上合同对方必须能对 ERP；年度价 `supplier_name` 只是报价来源旁注。

主数据给出稳定身份：**ERP 代码** 对外系统（合同 / ERP，不进工艺列）。  
本平台规范名 = **全称**，对齐现网工艺确认、对齐基地「规范名」：点选落库、覆盖键都用它。全称是主键，**可以改**；仍被直接下一跳（工艺非空厂名、采购对象非空对方）引用则引擎 `RESTRICT`，不能改。改成功后旧全称收成别名（S4），间接表字符串不级联改。  
与基地 / 项目不同：那两处产品不提供改主键；供应商提供，但有零件或已指定对方时改名会被拒。这是预期，不是和宪法冲突。  
**缩写** 只给人看（下拉旁注、窄列），不进 `stamping_supplier`。  
**别名（一条多条）** 吸收表头乱写。核对用全称 / 缩写 / 别名 / ERP，工艺与采购对象落库只用规范全称。

钢厂 / 紧固件商（`material_mill`）不是本文，仍在一事一议 / 材料侧。

---

## 2. 已定规则

| # | 规则 |
|---|------|
| S1 | 供应商只在本文。不挂在项目下。不替代基地 |
| S2 | 与基地同属主数据；**不依赖** 项目 / 冲压 / BOM / 核价。按供应商写入的下游依赖本文 |
| S3 | **建档只在供应商切片。** 一览表抽屉手工增加，或上传页 Excel。下游找不到就回一览表 / 上传页补。禁止下游代建、禁止 `get_or_create`、禁止启动或脚本从下游 `DISTINCT` 插入。工艺确认表、年度价、采购对象**不能**当供应商主数据的上传入口 |
| S4 | 必填 **缩写**、**全称**、**ERP 代码**。三者各自唯一，且与别名同一解析命名空间互斥。全称是主键，**产品提供修改**。缩写 / ERP **也可改**（非主键，外键不管）。改后仍须互斥。**改全称成功后**：旧全称写入本行别名（若尚未占用命名空间）；新全称若已是本行别名，先删该别名再改主键。间接表（年度价 / 加工费 / 核价结果）不级联改名，靠这条别名让 `expand_for_query` 仍能筛到 |
| S5 | **点选**供应商，选项只来自本文，禁止自由输入。年度价 **Excel 导入除外**（S15，档案，允许乱写） |
| S6 | 工艺表头厂名经 `require_enabled` 解析为规范全称才准入。命中全称、缩写、ERP 代码或**任一条别名**即同一家。不能当建档入口。对上后落库写规范全称，不能按表头原文落库，也不能改写成缩写 |
| S7 | 不从下游表 `DISTINCT stamping_supplier` / `supplier_name` 发明自己 |
| S8 | **启用 / 禁用** 仍要。已启用才允许新引入（写门禁路径）。不做生效/失效日期、不另做暂停。禁用不是删除。**外键不管启用**：只认父行在不在。禁用后已有工艺 / 已指定采购对象仍可挂着 |
| S9 | **修改与删除同时支持**（宪法 §4.3）。直接下一跳子表声明 `ON UPDATE RESTRICT` + `ON DELETE RESTRICT`。改主键 / 删除只动供应商自己；仍被引用 → `IntegrityError` → `BusinessException("仍被引用，不能修改")` / `BusinessException("仍被引用，不能删除")`。**禁止**文案点名工艺/采购对象，禁止本切片 `count` 子行 / import 子 Model。父 Model **禁止** `relationship` 指向下一跳。启用/禁用、改缩写/ERP 是改非主键，外键不管 |
| S10 | **间接表、加 FK 之前的工艺行，允许乱写全称变体。** 禁止批量 `UPDATE` 改历史。读 / 覆盖删除 / 列表筛用 `expand_for_query`。**加 FK 之后**：`stamping_parts` / 采购对象非空值必须是规范全称，这两列不再允许乱写。乱写只还活在加工费、核价快照、年度价、溯源（不是下一跳） |
| S11 | **工艺确认上传写门禁（第一期已落地）。** 表单不选冲压工厂。Parser 抽出厂名后 `require_enabled`。抽不出 / 未登记 / 已禁用 → 硬停。对上后 **`stamping_supplier` 只写规范全称**。禁止从文件发明身份。布点仍不认供应商（APQP） |
| S12 | **采购对象改供应商写门禁（第二期）。** 指定或改成非空必须 `require_enabled`。请求里的空串在 Service **收成 `NULL` 再写库**，不跑门禁。列上禁止 `''`。点选细则见采购对象指定设计 |
| S13 | **一条供应商可挂多条别名**（0～N，可随时加）。专吃工艺确认表乱写 / 乱定的厂名。别名只用于解析与核对；下游列不存别名原文。创建时别名可空，对不上表头就回一览加别名，禁止因此把原文入库 |
| S14 | **核算不构成约束。** 零件核价 / 加工费 / 模具费 / 总成 / 引擎的 **calculate、ready、能否开算** 不调用 `require_enabled`，不因主数据未登记或已禁用拒绝核算。本文只管业务列 **写门禁路径** 的新写入或改成非空，以及列表 / 导出 / 覆盖删除等 **读路径** |
| S15 | **年度价 `supplier_name` 是报价档案，不是写门禁。** 只给核算抄 `vendor_name` 用，不是合同对方，不是工艺身份。Excel 导入非空 **不** 跑 `require_enabled`，允许空、允许历史乱写（S5 的例外）。列表手工编辑改为下拉（可空），选项来自本文，禁止自由打字；保存不因未登记/已禁用硬停。禁止从年度价发明主数据。不得用年度价厂名顶替采购对象指定。**不是下一跳，不加 FK** |
| S16 | **外键只加在设计图直接下一跳。** ① `stamping_parts.stamping_supplier`。② `bom_procurement_objects.supplier_name`（**可空 `NULL`**）。禁止给加工费 / 模具费 / 核价结果 / 日志 / 年度价 / 文件溯源 / LLM 再挂。别名附属行 `CASCADE`，不是下一跳。**落地顺序见 §3** |

钢价、冲次单价不按供应商写，不走本文。

冲压工厂不是基地、不是项目。同一家厂服务多座基地、多个项目 = **一行**，禁止按基地区成两条。

---

## 3. 位置

```
基地               ★ 位置绝对上游
供应商             ★ 对方绝对上游（与基地平行，互不隶属）
    │
    ├── 项目（只依赖基地；不依赖供应商）
    │
    └── stamping / bom / costing   写门禁路径先问本文；年度价只读选项、不门禁
```

下游继续存字符串。工艺 / 采购对象 **非空** 值 = **全称**。采购对象 **允许 `NULL`**（未指定）。年度价列可以是规范全称、空、或历史乱写（S10 / S15），**无 FK**。

引用保护（宪法 §4.3）：**子声明、父不知；只拦直接下游。**

```
suppliers.full_name
    │
    ├── supplier_aliases.full_name     附属行 CASCADE（同切片，不是下一跳）
    │
    ├── stamping_parts.stamping_supplier
    │      ForeignKey(..., ondelete="RESTRICT", onupdate="RESTRICT")
    │      加 FK 之后非空 = 规范全称。NULL 不引用、不挡删。
    │      现网列可空；S11 新包不写空。历史空厂名零件加 FK 前应再传覆盖，否则删供应商时这些行不挡（接受则写进落地清单）
    │
    └── bom_procurement_objects.supplier_name
           ForeignKey(..., ondelete="RESTRICT", onupdate="RESTRICT")
           **可空。** 未指定 / 清空 / 自制清空 = NULL，不是空串。
           NULL 不引用供应商，不挡改主键、不挡删除。
           非空必须是已有全称（存在即可，不要求已启用）。
```

父 Model **禁止** `relationship` / import 冲压件或采购对象。拦改主键/删除的是数据库，不是供应商去 `count` 零件。间接下游（加工费、模具费、核价结果、日志、年度价、溯源、LLM）**不加**供应商外键。改全称成功后这些表里的旧字符串不改；靠旧全称别名（S4）筛。

**加 FK 顺序（写死，S16）：**

1. 工艺：凡 `stamping_parts.stamping_supplier` 非空且不等于任一 `suppliers.full_name` 的包，**再传工艺覆盖**成规范全称（S11）。禁止 `UPDATE` 乱写（S10）。空厂名行同样覆盖或删包，避免删供应商留下无厂名零件。  
2. 采购对象：先加可空列；只写规范全称或 `NULL`。现网尚无此列则没有脏数据。  
3. 再改子 Model 声明 FK。非空对不上主键 → DDL 失败，回到步骤 1。  
4. 别名仍 `CASCADE`，与 RESTRICT 子表可以同时存在：改主键时有零件/非空对方则整单失败，别名也不变。

只按 `location` 写的路径（钢价、冲次单价）不过本文。  
按供应商 **写入且走门禁** 的路径：先过本文（已启用）。外键只保证「全称在主数据里」，不管启用。**核算不过本文**（S14）。**年度价不过 `require_enabled`**（S15）。列表 / 导出等 **读** 路径可用 `expand_for_query`。

---

## 4. 切片与入口（形态已落地；第二期补写与 FK）

| 项 | 定稿 |
|---|------|
| 切片 | `masterdata`（与基地、项目同一切片）。宪法 §4.1 上游 / 基础数据已含 `masterdata` |
| 代码 | `app/models/masterdata/supplier.py` · `routers/masterdata/supplier/` · `services/masterdata/supplier/` · `repositories/masterdata/supplier/` · `parsers/masterdata/supplier_parser.py`；前端 `static/js/features/masterdata/supplier/{upload,list}/` |
| 表 | `suppliers`（主键 `full_name`，`String(100)`，与年度价 `supplier_name` 同宽）· `supplier_aliases`（附属行）。凡存规范全称的业务列统一 `String(100)`，见 §5.6 |
| HTTP | `/api/masterdata/suppliers` **只给供应商两页**。下游上传/计算/列表下拉**不另开**这套 HTTP：各切片沿用现有接口，Service 内调本切片。避免工艺上传权限绑 `menu:supplier-upload` |
| 前端 | 侧栏 **供应商** 二级分组：叶子 **上传** + **一览表**。Hash `#/supplier-upload` / `#/supplier-list`；兼容 `#/supplier` → `supplier-list` |

基地 / 项目 Model **禁止** `relationship` 指向供应商。供应商 Service **禁止** import 冲压 / BOM / 核价（S2）。下游 Service **可以**调 `SupplierService`。

侧栏位置、权限树、上传/一览 UI、`pageMeta` **第一期已按本节落地**。第二期不改菜单树形态；**补** `op:supplier-list:delete`，一览编辑改为可改缩写/全称/ERP，并提供删除。供应商 HTTP 增加 `DELETE` 本体；`PATCH` 放开主键与缩写/ERP。

```
主数据 → 基地（单叶）→ 项目（上传/一览）→ 供应商（上传/一览）
```

权限：`menu:supplier` 分组；`menu:supplier-upload` + `op:…:view` / `upload`；`menu:supplier-list` + `op:…:view` / `export` / `create` / `update` / **`delete`**。`update` 含启用禁用、别名、**改缩写 / 全称 / ERP**。`delete` 删供应商本体（S9）。第二期要补 `op:supplier-list:delete` 与一览删除按钮；改主键走已有 `update`，编辑抽屉字段改为可改。

点选展示「缩写（全称）」，`value` 是全称。下游找不到（写门禁路径）Toast 带 `#/supplier-list`，**不要**在工艺/采购对象页内嵌创建表单。

一览 **禁止** 再打工艺 / 年度价 HTTP 去拉 `DISTINCT` 当「待补清单」（S2 / S7）。

---

## 4.1 第二期落地清单（本次）

**采购对象（S12，必做）**

| 文件 / 位置 | 动作 |
|-------------|------|
| `app/services/bom/…` 采购对象写路径 | 非空 → `require_enabled`，落规范全称。**`''` / 只空白 → `NULL`**，不跑门禁。再生成带回：父行还在则原样写入（可已禁用）；父行已不在 → 该行落 `NULL`，不要整次生成因 FK 失败 |
| 采购对象列表前端 | 确认抽屉远程检索已启用供应商（禁止一次拉全量）；已审禁用；核对区无此控件；Toast 深链 `#/supplier-list` |
| 采购对象 Excel 批改 | 独立上传页，见 [bom-procurement-object-supplier-upload-design.md](../bom/bom-procurement-object-supplier-upload-design.md)。非空同一套 `require_enabled`；禁止当建档入口 |
| 列表 / 导出筛 | 可选 `supplier_name` / `has_supplier`；查询可用 `expand_for_query` |
| [bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md) | 实施对照；状态改为落地后改「已落地」 |

**年度价列表（S15，附带；不是门禁）**

| 文件 / 位置 | 动作 |
|-------------|------|
| 年度价列表编辑抽屉 | 供应商从文本框改为 `<select>`：空 + `list_enabled()`。禁止自由打字 |
| 年度价 Excel 导入 | **不**接 `require_enabled`。空 / 乱写 / 规范全称都按 Parser 原文（strip）入库 |
| 年度价列表筛 | **不强制**改成主数据目录；若加筛，用 `list_registered` + `expand_for_query` 属读路径，仍非门禁 |
| [bom-annual-part-prices-design.md](../bom/bom-annual-part-prices-design.md) | 锁死 S15，避免 implementer 误接 `require_enabled` |

**引用保护（S9 / S16，必做）**

| 文件 / 位置 | 动作 |
|-------------|------|
| `app/models/stamping/part.py` | **先**确认非空 `stamping_supplier` 都是 `suppliers.full_name`（再传覆盖）。再加 `ForeignKey(..., ondelete="RESTRICT", onupdate="RESTRICT")`。列可空；空不引用 |
| `app/models/bom/procurement_object.py` | 新增 `supplier_name`（若尚未有列）`String(100)` **nullable**；同一 `ForeignKey` `RESTRICT` / `RESTRICT`。空 = `NULL`，禁止 `''` |
| 供应商 Service | `PATCH` 可改 `full_name` / `abbreviation` / `erp_code` / `is_enabled`（互斥校验仍在）。改全称：先处理本行别名（S4），再 `UPDATE`；`IntegrityError` → 「仍被引用，不能修改」。`DELETE` 本体同理。「仍被引用，不能删除」。**禁止** `count` 工艺/采购对象 |
| 一览前端 | 编辑抽屉：缩写 / 全称 / ERP 可改。操作列加删除，确认后再 `DELETE`。失败 Toast 用上面两句 |
| `catalog.json` | 补 `op:supplier-list:delete`，再生成 `Perm.*`。不要抄进 `permission-design.md` §7 |
| [stamping-process-confirmation-design.md](../stamping/stamping-process-confirmation-design.md) | 注明本表是供应商下一跳 |
| [bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md) | 改为下一跳 + 可空 FK；去掉「不是下一跳」 |

**不要在第二期做：** 给年度价 / 加工费 / 结果表 / 溯源加供应商 FK；批量改写历史乱写；年度价上传硬停；从年度价代建供应商；签约报表；供应商父 Model `relationship` 指向子表。

---

## 5. 表结构

### 5.1 `suppliers`

| 列 | 说明 |
|---|------|
| `full_name` | 全称，**主键**，`String(100)`。本平台规范名。工艺 / 采购对象非空时存这个。**可改**（改主键，S9） |
| `abbreviation` | 缩写，唯一，`String(50)`。界面短名。**可改**（非主键）。**不**写入工艺列 |
| `erp_code` | ERP 代码，唯一，`String(50)`。对外身份。**可改**（非主键）。**不**写入工艺列 |
| `is_enabled` | 启用 / 禁用 |
| `sort_order` | 下拉与列表顺序。新建 = 当前最大 + 1。不提供手改排序 |
| 审计 | `AuditUserMixin` |

布尔用 `is_enabled`。禁止逻辑删除 / 软删冒充 S9。禁止 `is_paused`、生效/失效年月。物理删除走 `DELETE` + `RESTRICT`（S9）。

主键选全称：现网工艺确认与 `stamping_supplier` 已经是全称。**不要**把列改成整型 FK。子表继续存全称字符串，由外键盯住。

供应商 Model **禁止** `relationship` 指向冲压件 / 采购对象。别名同切片附属行，允许 `relationship` + `CASCADE`。

### 5.2 `supplier_aliases`

附属行，**不是**独立主数据。

| 列 | 说明 |
|---|------|
| `alias` | 别名，主键，`String(100)`；全局唯一 |
| `full_name` | `ForeignKey("suppliers.full_name", ondelete="CASCADE", onupdate="CASCADE")` |

**同一解析命名空间**（Service 创建供应商和别名时四面都要查）：别名不得等于任一缩写、全称、ERP 代码；缩写 / 全称 / ERP 代码彼此不得相同，也不得等于已有别名；strip 后非空。

### 5.3 种子

**无种子。** 禁止 `ensure_seed_if_empty`。禁止从零件/年度价 `DISTINCT` 插入（S3 / S7）。现网厂名已在一览手工建档（或历史上传 Excel）；缺的继续走上传页 / 抽屉，不准脚本发明。

### 5.4 上传页模板（已落地）

列：缩写、全称、ERP 代码、别名（可多条）。不要「启用」列。整单事务；已有主键跳过不覆盖。  
**同步上传**（HTTP 对齐 [vehicle-model-design.md](vehicle-model-design.md) §5.4；上传页无轮询见该文 §4.4）：请求 Session 内解析落库，返回 `ApiResponse[SupplierUploadResultVO]`（条数 VO），**无** `task_id`。建档 Excel 是名册量级，不是工艺大表。入口在宪法 §五同步 Excel 封闭名单；禁止改成 `start_upload`。  
`GET …/template` · `POST …/upload` · `GET …/export` · 一览 `page` + `size`。  
`PATCH /api/masterdata/suppliers/{full_name}`：可改 `full_name`（路径是旧全称，须 URL 编码）、`abbreviation`、`erp_code`、`is_enabled`。改全称仍被引用 → 400「仍被引用，不能修改」。  
`DELETE /api/masterdata/suppliers/{full_name}`：删本体（别名 CASCADE）。仍被引用 → 400「仍被引用，不能删除」。

### 5.4.1 直接下一跳外键（第二期）

只改**子 Model**，供应商 Model 不写子、不 import 子。

```python
# stamping_parts.stamping_supplier
ForeignKey("suppliers.full_name", ondelete="RESTRICT", onupdate="RESTRICT")
# 列可空；加 FK 后非空必须已是全称

# bom_procurement_objects.supplier_name
ForeignKey("suppliers.full_name", ondelete="RESTRICT", onupdate="RESTRICT")
# Mapped[str | None]；未指定必须 NULL，禁止空串
```

`onupdate` 与 `ondelete` 必须同时声明。禁止 `CASCADE` 用在这两张独立主数据上。

外键 **只检查父行存在**，不检查 `is_enabled`。写门禁（`require_enabled`）才管启用。

采购对象：**未指定就是 `NULL`。** HTTP/表单空串在 Service 收成 `NULL` 再 `UPDATE`。`NULL` 不挡改主键、不挡删除。非空指定才挡。

工艺确认：覆盖删光该厂零件、且采购对象该全称都是 `NULL` 之后，删除供应商会成功。列上 `NULL` 的历史零件 **不挡删除**——加 FK 前用覆盖上传清掉或接受孤儿。

顺序见 §3。禁止为加 FK 对工艺表批量 `UPDATE` 乱写。

### 5.5 不做的表与入口

| 不做 | 原因 |
|---|------|
| 按基地拆行 | 同一厂服务多座基地仍是一行 |
| 供应商↔项目关系表 | 工艺覆盖键已经是基地+厂+项目+版本 |
| 生效/失效、暂停 | 非 S8 范围 |
| 逻辑删除冒充删除 | S9 是真 DELETE + RESTRICT |
| 间接下游供应商 FK | 加工费 / 核价结果 / 年度价 / 溯源 / LLM 不是下一跳（S16） |
| 启动 / 脚本从下游灌入 | 批量走上传页 Excel |

### 5.6 业务列宽度（`String(100)`，第一期已落地）

| 表 / 列 | 宽度 |
|---------|------|
| 凡 `stamping_supplier` 业务列（零件、加工费、模具费及其日志、LLM 筛） | **100** |
| `bom_annual_part_prices.supplier_name` | 100（不动） |
| `upload_files.stamping_supplier` | 100（不动） |

**不加间接下游 FK**（S16）。禁止批量回填被截断的历史值（S10）。

---

## 6. 解析契约

查库、门禁、展开别名只发生在 **Service**。**禁止 Parser 调 Service / Repository**。**核算 orchestrator / ready 不调本文**（S14）。**年度价导入不调 `require_enabled`**（S15）。

规范化：输入 `strip`；空串不是供应商。不做全角转换、不发明未登记别名、不按拼音/包含关系模糊匹配。

| 方法 | 行为 |
|---|------|
| `resolve_canonical(raw)` | strip 后命中全称或缩写或 ERP 代码或别名 → **全称**；否则 `None` |
| `require_enabled(raw)` | 得到全称且 `is_enabled` → 返回全称。不存在 / 已禁用 → `BusinessException`，提示去一览表。**仅写门禁路径用这个**（§6.0） |
| `expand_for_query(raw)` | 先 `resolve_canonical`；返回 `[全称, 缩写, ERP 代码] + 该行全部别名`。读间接表历史行、覆盖删除、列表/导出筛。加 FK 后工艺主表值已是全称，展开仍无害（含旧全称别名）。**不**用于核算拦算，**不**用于年度价导入拒单 |
| `list_enabled()` | 已启用，按 `sort_order`。采购指定、年度价**列表编辑**下拉 |
| `list_registered()` | 全部已登记（含禁用）。列表筛选项 |
| `list_page(q, is_enabled, skip, limit)` | 一览表分页 |

列表筛选项必须来自 `list_registered()`，**禁止**再 `DISTINCT` 业务表当身份选项（S7）。用户选全称后，**查询条件**用 `expand_for_query`。

| 场景 | 方法 | 说明 |
|------|------|------|
| 工艺上传（解析后门禁，不点选） | `require_enabled(表头)` | **第一期已落地** |
| 采购对象指定 / 改 **写路径** 下拉 | `list_enabled()` | **第二期**；`value = 全称` |
| 年度价列表手工编辑下拉 | `list_enabled()` | **第二期附带**；可空；**不**接 `require_enabled` |
| 零件列表 / 加工费 / 零件核价等 **列表筛** | `list_registered()` | 含禁用；`value = 全称` |
| 用户选中某厂后的 **Repository 条件** | `expand_for_query(选中全称)` | `IN (...)` |
| 页内 HUD「冲压工厂数」 | 本表 `COUNT(DISTINCT stamping_supplier)` | 统计写法种数（S10） |
| 签约报表「已指定厂」筛 | 该页聚合 DISTINCT | 不是 `list_registered` 全量（§8） |

### 6.0 写门禁

下游 **走门禁的** 新写入或改成非空供应商字符串，一律 `SupplierService.require_enabled`。找不到 / 已禁用 → `BusinessException`，深链 `#/supplier-list`，不代建。落库只写**规范全称**。

| 路径 | 何时 | 期 |
|---|---|---|
| `require_enabled` | 工艺确认表上传（表头厂名解析后准入） | **第一期已落地**（S11） |
| `require_enabled` | 采购对象行指定或改成非空对方 | **第二期**（S12）。清空不跑；再生成带回不跑 |
| **不跑** `require_enabled` | 年度价 Excel / 列表保存 `supplier_name` | **S15**。列表只用下拉，不是门禁 |

不要包一层 `require_supplier` 分发器；点名 `require_enabled`。

**第一期硬路径（工艺确认上传，已落地）：** 表单只选文件 → Parser 抽厂名 → `require_enabled` → 落规范全称；覆盖删除 `stamping_supplier IN expand_for_query(规范全称)`。Router Form 只收 `file`。布点不加供应商。

**第二期路径（采购对象改供应商）：** 仍走采购对象切片 PATCH，不新开供应商 HTTP。非空 body → `require_enabled`，落规范全称；`''` / 空白 = **`NULL`**，不跑门禁。禁用后不准新指定、不准改成该厂；行上已有全称仍可查（FK 仍成立）。页面下拉 `list_enabled`（value = 全称）。再生成带回：不跑 `require_enabled`；写入前若该全称已不在 `suppliers` → 该行 `NULL`，生成继续。确认/审核锁定、自制清空归指定供应商设计。

**年度价（S15，不是门禁）：**

1. **Excel：** Parser 抽出 `supplier_name` 后 strip；空 = `NULL`/空串按现网；非空 **原样入库**，不 `require_enabled`，不对不上就整单失败，不把原文建成新供应商。  
2. **列表手工编辑：** 控件改为下拉，选项 = 「（空）」+ `list_enabled()`，展示「缩写（全称）」，`value = 全称`。禁止 `<input>` 自由打字。选空 = 清空。选中某厂 = 写入该全称（顺带规范，仍不是拒单门禁）。  
3. **已有乱写：** 编辑抽屉打开时，若当前值解析不到已启用行，仍把当前值做成一项（只读展示或额外 option），避免一打开就把档案清掉。用户可以改成下拉里的厂，也可以改成空。不要在保存其它字段时偷偷 `require_enabled`。  
4. **已审核行** 仍按年度价现网：须先反审核才能改（含改供应商下拉）。  
5. 核算抄 `vendor_name = supplier_name` 时按行上字符串抄，不过本文。

### 6.1 写

门禁分层见 §6.0。工艺 / 采购对象落库只写**规范全称**。

年度价可空。空 = 不校验、不写。非空 Excel 不门禁。列表只允许点选或清空。

覆盖上传工艺（同基地 + 厂 + 项目 + 版本整包替换）：删除范围必须 `stamping_supplier IN expand_for_query(规范全称)`。

### 6.2 读

**不改写**已有业务表里的乱写全称。列表 / 导出 / 覆盖删除前的查询用 `expand_for_query`。

已禁用：不准 **写门禁路径** 新引入；已有结果仍可查、筛选里用 `list_registered()`。年度价下拉只用 `list_enabled`；已禁用厂若已在行上，按 §6.0 第 3 条保留，不要逼用户立刻改掉。

### 6.2.1 核算不构成约束（S14）

**零件核价、加工费、模具费、总成核价、核价引擎** 的 `calculate` / `ready` / 能否开算：**不**调用 `require_enabled`。核算只消费已有字符串。年度价缺供应商或乱写 **不挡算**（S15）。

### 6.3 禁用 / 修改 / 删除

| 动作 | 行为 |
|---|------|
| 禁用 | `UPDATE is_enabled`。已有工艺 / 年度价 / 采购对象行不改。外键不管 |
| 改缩写 / ERP 代码 | `UPDATE`。非主键，外键不管。仍须命名空间互斥 |
| 改全称（主键） | ① 新全称若等于本行某别名，先删该别名。② `UPDATE` 主键。③ 成功则旧全称插入别名（占用命名空间则 `BusinessException`，整单回滚）。别名表 `ON UPDATE CASCADE` 仅在 UPDATE 成功时跟着走。工艺 / 采购对象 **RESTRICT**：仍有非空引用 → `IntegrityError` → `BusinessException("仍被引用，不能修改")`。禁止点名子表。间接表不改 |
| 删除 | 只 `DELETE` 自己。别名 `ON DELETE CASCADE`。仍被工艺非空厂名或采购对象**非空**对方引用 → `IntegrityError` → `BusinessException("仍被引用，不能删除")`。采购对象全是 `NULL`、工艺该全称已无行 **不挡**。工艺列 `NULL` 的零件不挡——加 FK 前应覆盖掉 |

没有下一跳非空引用时改全称、删除都会成功——预期（只建档、采购对象都未指定、工艺已覆盖删光）。有零件或已指定对方时改名/删除会被拒——预期。与基地「规范名创建后不改」不同，不是漏洞。

### 6.4 工艺覆盖键

现网唯一键仍是：基地 + 冲压厂 + 项目 + 版本 + 零件号。冲压厂列继续存**全称**。版本仍从文件解析。

---

## 7. 找不到 / 引擎

| 情况 | 去哪 |
|---|------|
| 工艺表头 / 采购对象点选对不上 | 一览表给已有行追加别名，或新建。**禁止**把原文写入工艺列 / 采购对象列 |
| 有行但已禁用 | 一览表改为启用；下游不代建 |
| 年度价 Excel 厂名对不上 | **允许入库**（S15）。以后要在列表里改成规范名，用下拉 |

上传/采购对象页可深链 `#/supplier-list`，不得内嵌创建。

引擎入口仍是 **基地 + 年 + 月**，不过本文。

---

## 8. 谁改读本文 / 谁不要动

**第一期已做（对照，不要回退）：**

- 工艺确认上传写门禁；列宽；零件 / 加工费 / 零件核价列表筛 `list_registered` + `expand_for_query`
- 文件溯源：门禁后写入规范全称；历史乱写不改写
- LLM：只读本表 Model，禁止调 SupplierService

**第二期要改：**

- 采购对象指定 / 改供应商：非空 → `require_enabled`；`''` → `NULL`（S12）
- 年度价**列表编辑**控件改为下拉（S15）。导入 **不要**接门禁
- 下一跳 FK（先覆盖工艺再 DDL）+ 一览改主键（旧名收别名）/ 删除（S9 / S16）

**不要改：**

- 钢价、冲次单价、废料月度销售价
- 模具布点 / 模具单价 / 检具费（不认供应商；**不是**下一跳，不加 FK）
- 成品核价不认冲压工厂
- 核算 calculate / ready 不接 `require_enabled`（S14）
- 给年度价 / 加工费 / 结果表 / 日志 / 溯源 / LLM 加供应商 FK（S16）
- 为加 FK 对工艺表批量 `UPDATE` 乱写（S10）
- 全库历史行批量改写成规范全称（S10）
- 钢厂 / `material_mill` 收进本文
- 供应商切片 `count` 下游 / import 冲压·BOM
- 签约报表下拉改成 `list_registered` 全量（未指定的厂不应出现在合同附件筛里）
- 把年度价 Excel 做成第二套供应商上传
- 采购对象用空串 `''` 代替 `NULL`

---

## 9. 范围

**第一期已做：** 切片上传 + 一览 + 别名 + 启用禁用；工艺确认写门禁；列宽；读路径筛；核算不过本文。

**第二期做：** 采购对象改供应商（S12，**可空 `NULL`**）；年度价列表下拉（S15）；下一跳 `RESTRICT`（先覆盖工艺再 DDL）；一览改主键（旧名收别名）/ 改缩写与 ERP / 删除。

**不做：** 年度价 Excel / 保存接 `require_enabled`；年度价加供应商 FK；为加 FK 批量 `UPDATE` 工艺乱写；把年度价当建档入口；用年度价顶替采购对象指定；本期做签约报表；把工艺表头原文或缩写写入 `stamping_supplier`；为每一种乱写新建一条供应商；启动或脚本从下游表灌入种子；钢厂主数据；一件对多家；合同号/单价；按基地区分同一供应商成两条；全库整型外键；间接下游 FK；采购对象列存 `''`；生效/失效日期；暂停；逻辑删除；手改 `sort_order`；在核算 calculate / ready 接 require_enabled 或拦算（S14）；父切片 `count` 子表 / 文案点名子切片。

侧栏「供应商」与「基地」「项目」分开展示，不要做成同一张表。

---

## 10. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-08 | 定稿：全称主键；缩写 / ERP；启用禁用；别名 0～N；工艺上传门禁 S11；采购 S12；落库规范全称 |
| 2026-09-08 | 补 §5.6 列宽；`list_enabled` / `list_registered`；工艺解析后门禁 |
| 2026-09-08 | **S14**：核算 calculate / ready 不过本文 |
| 2026-09-08 | 第一期落地后整理：**第二期 = 采购对象 S12**；**S15 年度价是报价档案**：导入不门禁，列表手工编辑只改下拉、可空 |
| 2026-09-08 | **S9 / S16**：修改与删除同时支持。下一跳仅工艺确认表 + 采购对象表，`RESTRICT` / `RESTRICT`。采购对象 `supplier_name` **可空（NULL）**，空不挡删/改主键 |
| 2026-09-13 | §5.4：建档 Excel **同步**上传（权威口径）；不在 §9 复述 |
| 2026-09-13 | §5.4：与项目文档分工：HTTP 对 §5.4，UI 无轮询对 §4.4 |
