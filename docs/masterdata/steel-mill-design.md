# 钢厂 — 主数据设计

> 状态：**已落地**。档案、导入收口、按 `steel_mill_id` 关联已经在现网。§11、§12 已按代码勾完。
> 关联：`app/models/yishiyiyi/steel_base_price.py`、`app/models/yishiyiyi/steel_price_policy.py`、`app/services/yishiyiyi/policy/match/adjustment_common.py`、`docs/masterdata/steel-grade-category-design.md`、`docs/masterdata/location-design.md`  
> 原则：钢厂是档案，不是 Excel 里的一串字。页面上显示缩写，全称用来对表头，停用之后不能再选用，与供应商一致。基准价、加减价新写入必须带 `steel_mill_id`。对不上档案，整本不入库。基准价行上的 `steel_mill` 保留 Excel 原文，供溯源；全称和 id 另加两列。之后基价与政策按这个 id 关联。

---

## 0. 一句话

> **钢厂主数据一家一行。缩写显示在页面上，全称用来对表头，这一行可以挂多条别名（如「山钢」与「山钢(新)」收到同一个 id）。停用之后不能再选用。基准价导入、加减价导入先把表里的钢厂文字收成档案 id；有一家对不上或已停用，整本回滚，并提示到钢厂页手工增加或重新启用。基准价落库：`steel_mill` 用 Excel 原文，另写全称和 id。加减价落库：`steel_mill` 写成全称，并写 id。核价、中标厚度按 `steel_mill_id` 配。代码里的钢厂别名表和「(新)」自动互通废止。**

维护页在 **主数据 → 钢厂**，与牌号分类并列。设置仍是个人资料、系统设置、用户、操作日志。

---

## 1. 为什么做

现网钢厂没有档案。基准价、加减价各存各的名字，对上对不上靠 `adjustment_common.py` 里的 `_STEEL_MILL_ALIASES`，外加任意名字与「(新)」自动互通。

库里同一时期能看到的写法（2024-03 至 2026-08）：

| 来源 | 写法 |
|------|------|
| 基准价 | VAMA、包钢、唐钢、宝钢、山钢、本钢、涟钢、邯钢、鞍本、鞍神、首钢、马钢 |
| 厚度加减价 | 上表里的短名，再加上 TAGAL、包钢(新)、唐钢(新)、宝钢(新)、山钢(新)、涟钢(新)、邯钢(新)、马钢(新)、首钢最新、鞍钢集团、鞍神(新)、宝钢 (2)、首钢 (2)、山钢 (2) |

猜法同时偏松、偏漏：

| 现网 | 问题 |
|------|------|
| 「本钢」与「鞍钢集团」在代码里互认 | 业务上未必是同一家。鞍本、鞍神又是另外的名字，代码并不互认 |
| 任意名字自动加上 / 去掉「(新)」 | 「马钢」能配上「马钢(新)」，规则写在代码里，档案页改不了 |
| 「首钢」与「首钢最新」 | 不在别名表里，也不符合「(新)」规则，厚度政策对不上基准价 |
| 版式处理器按 sheet 名关键字选 | 「马钢(新)」「鞍钢集团」「华菱」决定用哪套解析，不决定是哪一家钢厂 |

牌号已经走档案：缺档整批拒绝，落库写档案上的 `grade`。钢厂按同一标准收口。

---

## 2. 定稿约定

| 约定 | 内容 |
|------|------|
| 产品名 | **钢厂** |
| 表 | `steel_mills` + 附属 `steel_mill_aliases` |
| 归属 | **`masterdata`**。一事一议、核算都读。禁止放 `yishiyiyi` / `costing` / `settings` |
| 入口 | 主数据 → **钢厂**。`#/steel-mill`。API `/api/masterdata/steel-mills` 只给本页 |
| 权限 | `menu:steel-mill` 挂在 `menu:masterdata` 下；`op:steel-mill:view/create/update/delete` |
| 主键 | `id`（整数，自增）。关联只用它 |
| 缩写 | `abbreviation`。页面上的字。全库唯一 |
| 全称 | `full_name`。用来对 Excel 表头。全库唯一。钢厂允许缩写与全称相同 |
| 别名 | **一家多条。** 每条全局唯一，都指向同一 `steel_mill_id`。全称「山钢」再加别名「山钢(新)」，两处写法都命中这一家 |
| 启用 | 与供应商一致。已启用才能新选用。停用后不能再选。停用不是删除，已落库的行仍在 |
| 谁能写档案 | **只有本页。** 基准价、加减价导入不插钢厂、不补别名 |
| 谁必须带 id | `steel_base_prices`、`steel_price_policies`。新写入 `steel_mill_id` 非空 |
| 基准价落库 | `steel_mill` 存 Excel 原文，溯源用。另加 `canonical_steel_mill`（全称）和 `steel_mill_id`。不把原文改成全称 |
| 对不上 | **整本退回**：这一份上传文件 rollback，一行不留。不存在时提示到钢厂页手工增加 |
| 之后怎么关联 | 同年月的基准价与加减价按 `steel_mill_id` 相等。不再调用 `steel_mill_matches` / `steel_mill_aliases` |

依赖：

```text
写入
  主数据钢厂页  →  本切片 CRUD（唯一写入通道）

读取 / 收口
  基准价、加减价、中标厚度、钢材联动、LLM、以及以后的调用方
      →  钢厂 Service 的解析（§5.2），返回 id
      →  本切片 Repository 只被这个 Service 用来装对照表

禁止
  masterdata → yishiyiyi / costing
  下游往 steel_mills / steel_mill_aliases 插行
  Parser 调主数据（Parser 只交出表里的钢厂原文）
  用 DISTINCT 现网 steel_mill 自动建档
```

---

## 3. 入口为什么在主数据

侧栏「设置」是账号和系统参数。基地设计已把业务档案放在主数据，不并进设置。钢厂与牌号分类是同一类：下游导入前必须先有档案。

落地后主数据子菜单顺序：基地、项目、供应商、牌号分类、**钢厂**。

---

## 4. 表结构

### 4.1 `steel_mills`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | 自增。创建后不改。关联只用它 |
| `abbreviation` | String(50) | ✓ | **缩写。** 页面主字。全库唯一。可改 |
| `full_name` | String(50) | ✓ | **全称。** 对表头的规范字。全库唯一。可改 |
| `is_enabled` | Boolean | ✓ | 默认 true。停用后不能再选用 |
| `sort_order` | Integer | ✓ | 列表顺序。新增时取当前最大 + 1，本页不手改 |
| `remark` | Text | | |
| AuditUserMixin | | ✓ | |

同一家允许缩写与全称相同。现网表头就是「山钢」这种短名，页面上也显示这个字。供应商要求缩写、全称、ERP 互不相同，钢厂不抄那条。

缩写、全称、别名仍在同一个解析空间里互斥：别名不得等于任一缩写或全称；这家的缩写不得等于另一家的全称或别名。ASCII 忽略大小写（`vama` 与 `VAMA` 是同一家）。中文按去空格后的原文比较。全角括号先收成半角再比较、再入库。

`id` 不改。改缩写只影响页面上的字，不回写基准价原文。改全称不回写已落库的 `canonical_steel_mill` 和加减价 `steel_mill`；之后新导入写新的全称。旧全称若还要能对上表头，先收成这条的别名再改。

### 4.2 `steel_mill_aliases`

附属行。删钢厂时 CASCADE。不是独立主数据。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `alias` | String(50) PK | ✓ | 全局唯一。比较规则与全称相同 |
| `steel_mill_id` | Integer FK | ✓ | → `steel_mills.id`，`ondelete="CASCADE"`，`onupdate="CASCADE"`。不唯一，一家多条 |

一家钢厂对应多行别名：`alias` 唯一，`steel_mill_id` 不唯一。头表 **不** `relationship` 别名，**不** import 别名 Model。别名按 `steel_mill_id` 由本切片 Repository 读写。

别名不得等于任一缩写或全称，也不得等于另一家的别名。同一家不要把全称再登记成自己的别名。全称、缩写本身已经能命中，不必再占一条别名。

覆盖方式：全称写「山钢」，缩写也写「山钢」，别名可以同时写「山钢(新)」以及以后表头出现的其它写法。导入见到其中任一原文，都落到这一个 `id`。基准价原文列保持表里的字，全称列写 `full_name`。加减价的 `steel_mill` 写成全称。再加第三条别名只加一行，不改匹配代码。别名之间没有优先级。

### 4.3 事实表增加的列

一事一议基准价 `steel_base_prices` 加两列。原来的 `steel_mill` 不改含义：Excel 单元格里的钢厂原文，和 `excel_filename`、`sheet_name`、`excel_row` 一起做溯源。打开源文件时对得上这一格，不换成全称。

| 列 | 类型 | 必填 | 说明 |
|----|------|------|------|
| `steel_mill` | String(50)，已有 | ✓ | **原文。** 落库不改成全称。只去前后空格；全角括号、`(新)` 等保持单元格里的样子 |
| `canonical_steel_mill` | String(50)，新增 | ✓ | **全称。** 命中档案后写入 `steel_mills.full_name`。页面上不拿这列当主字 |
| `steel_mill_id` | Integer，新增 | ✓ | **档案 id。** → `steel_mills.id`，`ondelete="RESTRICT"`，`onupdate="RESTRICT"` |

加减价 `steel_price_policies` 只加 `steel_mill_id`（同一外键）。它的 `steel_mill` 写成全称，不加第三列。

关联、唯一键都认 `steel_mill_id`。基准价列表：主字用缩写（按 id 读档案），溯源列用原文 `steel_mill`。全称在 `canonical_steel_mill`，用来对表头，不代替页面主字。

三个库里的基准价、加减价和钢材联动结果已经对齐。基准价的 `steel_mill` 仍是原文，另有 `steel_mill_id` 和 `canonical_steel_mill`。加减价里原来的别名已经改成全称，并写上 `steel_mill_id`。启动不再改这些行。以后钢厂页改缩写、改全称，也都不回写这些表。

唯一约束把字符串 `steel_mill` 换成 `steel_mill_id`：

| 表 | 唯一键 |
|----|--------|
| `steel_base_prices` | `year, month, location, steel_mill_id, category_name, grade, thick, width` |
| `steel_price_policies` | `year, month, steel_mill_id, category_name, policy_type, grade_value, base_thickness` |

`steel_prices`（钢材联动结果）本期也加 `steel_mill_id`，取值来自命中的那条基准价，不重新猜。唯一键里的 `steel_mill` 同样换成 `steel_mill_id`。外键策略与上表相同：`RESTRICT`。这是身份引用，不是宪法 §3.3 那张溯源指针名单，禁止 `SET NULL`。

---

## 5. 档案页

单页，壳对齐供应商一览，不另做上传页，不加 ERP。页头说明与供应商同一句：

> 缩写显示在页面上，全称用来对表头。停用之后不能再选用。

HUD 密表。列：缩写（主字，14px 粗体）、全称、别名、状态、操作。别名顿号分隔，没有则留空。搜索「缩写 / 全称 / 别名」。状态胶囊：全部 / 已启用 / 已禁用。仍走 `page-size.js`。

| 操作 | 规则 |
|------|------|
| 新增 | 缩写、全称都必填。与已有缩写、全称或别名冲突 → 409 |
| 编辑 | 可改缩写、全称、启用状态、备注、别名 |
| 别名 | 抽屉里逐条加、逐条删，一家不限条数。空串、与任一缩写或全称相同、与已有别名冲突，都拒绝 |
| 删除 | 仍被基价、加减价或钢材联动结果引用 → `仍被引用，不能删除`。引擎 `IntegrityError` 翻译，本切片不去数子表 |
| 启用 / 停用 | 改非主键，外键不管。停用后不能再选用：导入整本退回；下拉和点选里不再出现。已经落库的行保留，不因停用改写 |

选用与供应商一致：新写入、新点选只给出已启用的钢厂。基准价、加减价、联动计算里若要选钢厂，展示缩写；需要区分时写成「缩写（全称）」。选中后落库用 `id`，不用全称当外键。找不到或已停用，提示到 `#/steel-mill` 手工增加或重新启用，不在业务页里嵌创建表单。点选的选项来自 §5.2 的已启用清单，不各页自己查表。

### 5.2 对外解析（返回 id）

给基准价、加减价政策，以及中标厚度、钢材联动、LLM 和以后的调用方。不另开 HTTP。上传和计算继续走各自现有接口，Service 里调本方法。钢厂页的 CRUD 接口不承担这件事。

一家钢厂加上别名，全库只有几十个字。解析开始时 **一次** 读出全部缩写、全称、别名，装成「规范化写法 → 这一家」的对照表，本请求里再用。不对每一行各打一次 SQL。

规范化与 §6 相同：去前后空格，全角括号改半角，ASCII 忽略大小写。这只用于查表，不改调用方手里的原文。

| 方法 | 做什么 | 返回 |
|------|--------|------|
| `resolve` | 一个原文查一家。没有则空 | `SteelMillHit` 或空 |
| `resolve_many` | 一本文件里的全部原文。对照表只装一次 | 原文 → `SteelMillHit`。没有的原文不在表里 |
| `require_enabled` | 新写入用。没有，或已停用，抛 `BusinessException` | 同一 `SteelMillHit` |
| `require_enabled_many` | 导入用。先扫完，缺的和停用的一次列完再抛 | 原文 → `SteelMillHit` |
| `list_enabled` | 下拉、点选 | 已启用的 `SteelMillHit` 列表，按 `sort_order` |

`SteelMillHit` 只这四项：`id`、`abbreviation`、`full_name`、`is_enabled`。调用方拿 `id` 落库和关联，拿缩写显示，拿全称写入 `canonical_steel_mill` 或加减价的 `steel_mill`。不要再查第二次。

`resolve` 对已停用仍返回这一家，并带 `is_enabled=false`。读历史、筛已有行可以用。`require_enabled` 才拒绝停用。禁止在调用方里用名称相等代替这次解析。

基准价导入、加减价导入只调 `require_enabled_many`。联动命中政策调 `resolve` / `resolve_many`，用返回的 `id` 比较。LLM 不调用这些方法，只读结果行上已经落下的 `steel_mill_id`。Parser 不调这些方法。

本期不做档案 Excel 导入、不做导出。避免把表里的乱名再灌进档案。

### 5.1 种子（落地必做）

种子一次写全。表为空时启动写入；已有任意行则跳过，不覆盖后来在页面上加的别名。

12 家全部启用，与基准价里的钢厂一致。缩写与全称先写成同一个短名，页面和表头都是这个字。别名与这两列同一次写入。一家可以多条。鞍钢集团、TAGAL 不是单独一家，都是鞍本。

| 缩写 | 全称 | 别名 |
|------|------|------|
| VAMA | VAMA | |
| 包钢 | 包钢 | 包钢(新) |
| 唐钢 | 唐钢 | 唐钢(新) |
| 宝钢 | 宝钢 | 宝钢(新)、宝钢 (2) |
| 山钢 | 山钢 | 山钢(新)、山钢 (2) |
| 本钢 | 本钢 | |
| 涟钢 | 涟钢 | 涟钢(新) |
| 邯钢 | 邯钢 | 邯钢(新) |
| 首钢 | 首钢 | 首钢最新、首钢 (2) |
| 马钢 | 马钢 | 马钢(新) |
| 鞍本 | 鞍本 | 鞍钢集团、TAGAL |
| 鞍神 | 鞍神 | 鞍神(新) |

三个库里的加减价已经按下面改完。别名仍留在种子里：空库第一次启动写入，以后导入同一表头还能对上。

| 现网原文 | 改成 | 现在在哪 |
|----------|------|----------|
| 包钢(新)、唐钢(新)、宝钢(新)、山钢(新)、涟钢(新)、邯钢(新)、马钢(新)、鞍神(新) | 各自去掉「(新)」的全称，并改 `steel_mill` | 加减价 |
| 宝钢 (2)、首钢 (2)、山钢 (2) | 各自去掉「 (2)」的全称，并改 `steel_mill`。括号前有一个空格，别名按这个字登记 | 加减价 |
| 首钢最新 | 首钢，并改 `steel_mill` | 加减价 |
| 鞍钢集团、TAGAL | 鞍本，并改 `steel_mill` | 加减价。档案不单列这两家 |
| VAMA、包钢、唐钢、宝钢、山钢、本钢、涟钢、邯钢、鞍本、鞍神、首钢、马钢 | 同名全称 | 基准价只填 id 和 `canonical_steel_mill`，`steel_mill` 保持原文。加减价、钢材联动结果里已是这些字的行只填 id |

基准价原文没有改。加减价里这些别名已经写成全称，并填上同一个 id。三个库不留空 id。

**不把「本钢」和「鞍本」收成一家。** 鞍钢集团、TAGAL 收到鞍本。鞍神仍是另一家。`华菱` 现网没有落库，不进种子。

---

## 6. 导入门禁

Parser 仍只解析出钢厂原文。收口在一事一议导入 Service，写入之前调用 §5.2 的 `require_enabled_many`。

比较：去前后空格，全角括号改半角；ASCII 忽略大小写。比较只用于查找，不写回基准价原文。命中全称、缩写或任一条别名即可，都是这一家。已停用的命中也算找到了这家，但按下面「已停用」整本退回，不能选用。命中后：

基准价：

- `steel_mill` = Excel 原文（只去前后空格）
- `canonical_steel_mill` = 档案 `full_name`
- `steel_mill_id` = 档案 `id`

加减价：

- `steel_mill` = 档案 `full_name`
- `steel_mill_id` = 档案 `id`

以下任一成立，**整本退回**，`BusinessException`，rollback。不存在与已禁用分开写，用户看到的是下一步去哪一页做什么。

| 情况 | 提示 |
|------|------|
| 原文对不上任何全称、缩写和别名（钢厂不存在） | 点名原文。基准价带 Excel 行，加减价带 sheet。句末固定：**请到钢厂页手工增加（#/steel-mill）**。本文件未写入 |
| 命中的钢厂已停用 | 点名缩写，写明已停用，不能再选用，请到钢厂页启用（`#/steel-mill`） |
| 基准价：同一文件里两种写法收到同一 `steel_mill_id`，并且业务键相撞 | 点名这两种写法收成了同一钢厂，本文件不合并、不覆盖 |
| 加减价：同一文件里两张表页收到同一 `steel_mill_id` | 整本退回，不再要求业务键相撞。点名表页和钢厂全称，并给出两条处理：改 Excel 删掉多余表页，或到钢厂页把两种写法拆成两家 |

不存在时的全文按这个样子（多家用顿号连在同一句里，仍只提示一次手工增加）：

```text
钢厂「首钢最新」不存在（加减价，sheet「首钢最新」）；钢厂「华菱」不存在（基准价，Excel 第12行）。请到钢厂页手工增加（#/steel-mill）。本文件未写入。
```

超过 20 处时列出前 20 个原文，并写总家数，手工增加那一句仍在最后。系统不代建、不把原文收成别名。用户到钢厂页手工增加（或给已有钢厂加别名、重新启用）后，再重新导入这一本。

基准价、加减价都仍是长任务。门禁在 `commit` 之前。手工新增、手工修改这两张表的钢厂，走同一套收口，不能绕过导入。

加减价不限 `THICKNESS`。政策头上的钢厂都收口，宽度等类型一并。

版式处理器不动。sheet 名仍用来选唐钢 / 马钢(新) / 首钢 / 鞍钢那套解析。解析出的文字再交给档案收口。

---

## 7. 关联

以前靠猜钢厂的那一段，加在 `app/services/yishiyiyi/policy/match/adjustment_common.py`。落地时整段删除，不迁到 `app/common/`，也不留半套给核价继续调用。

删掉这些：

- `_STEEL_MILL_ALIASES`（含「本钢 = 鞍钢集团」）
- `normalize_steel_mill`
- `steel_mill_aliases` 和「(新)」自动扩展
- `steel_mill_matches`
- `steel_mill_match_rank`
- `filter_candidates` 里按名称排序、按别名放行的部分

大类别名、阶梯区间、`base_thickness` 排序留在这个文件里。那不是钢厂身份。

去空白、全角括号只留在钢厂 Service §5.2，用来查 id。`adjustment_common` 不再导出第二套钢厂名字。

改调用：

| 位置 | 改成 |
|------|------|
| `costing/.../adjustments/thickness.py` | 同年、同月、`steel_mill_id` 相等，再按大类与阶梯。对不上就是没有这家的政策 |
| `winning_thickness/.../row_assembler.py` | 去重和组装用 `steel_mill_id`，不再 `normalize_steel_mill` |
| `filter_candidates` | 候选只留 id 相同的政策 |

一家基价对不上该公司的政策，就是没有这条政策，不要换一家名字接近的。

零件核价结果上的 `steel_mill` 快照本期不改、不加外键。它抄的是计算当时的全称。页面上若要显示，仍用缩写。

### 7.1 LLM 加减价异常比较

现网 `build_policy_mom_anomalies` 用 `_policy_ladder_key` 把阶梯串成一组，键的第一段是 `steel_mill` 名称。名称不同就不会拿来环比，于是「山钢」和「山钢(新)」各算各的，跳变看不出来。

落地后这条比较只认 `steel_mill_id`：

- 配对键用 `steel_mill_id`，再加大类、政策类型、牌号、厚度档、是否基准。不用 `steel_mill`，也不调用别名猜测。
- 分析只读加减价、基准价结果行上已经落下的 `steel_mill_id`。不调用钢厂 Service，不读钢厂档案表。
- 交给模型的钢厂字用结果行上的 `steel_mill`。这个字不参与是否同一家的判断。
- 问句里的钢厂筛选：先在本结果表上找到这个字对应的 `steel_mill_id`，再按 id 取出这家的全部行。

LLM 切片里凡是判断是不是同一家钢厂，都用结果行上的 `steel_mill_id`：加减价汇总、基准价异常、基准价环比相差、中标厚度汇总，以及问句筛选。不跨到钢厂切片。

---

## 8. 已有行

种子写完就改已有数据，不另等一版别名。顺序：

1. 建档案表，写入 §5.1 的全部缩写、全称和别名。
2. 基准价加上 `steel_mill_id`、`canonical_steel_mill`。加减价和钢材联动结果加上 `steel_mill_id`。用种子收口：命中则写入该 `id`。基准价同时写入全称，**不改** `steel_mill`。加减价把 `steel_mill` 改成全称。对不上的行不改字、不发明新钢厂。
3. 改完点名仍然空着的行（表、年月、原文）。按 §5.1，现网这三张表应当是零行。若不是零行，先把缺的写法补进种子再重跑，不带着空 id 上线。
4. 空 id 为零之后：列改为非空，加上 `RESTRICT` 外键，唯一键改为 `steel_mill_id`。
5. 接上导入门禁，再删 §7 的猜测函数。

禁止用 `_STEEL_MILL_ALIASES` 或「(新)」自动互通的结果来改已有行。改行与以后的导入共用档案收口。钢厂 Service 不查询、不更新这三张表。

---

## 9. 本期不做

| 不做 | 原因 |
|------|------|
| 放进设置菜单 | 与基地、牌号分类不是一类 |
| 档案 Excel 导入 | 乱名会绕过手工确认 |
| 从下游 `DISTINCT steel_mill` 建档 | 会把「包钢」和「包钢(新)」建成两家 |
| 预置本钢 = 鞍钢集团 | 那是现网猜测，不是档案 |
| 改版式处理器的关键字路由 | 版式不是身份 |
| 工艺 `material_mill`、供应商主数据 | 那是材料厂家 / 合同对方，见供应商设计 |
| 零件核价结果加钢厂外键 | 快照列，本期只保证联动结果带 id |

---

## 10. 落地时的代码位置

```text
app/models/masterdata/steel_mill.py
app/repositories/masterdata/steel_mill/
app/services/masterdata/steel_mill/service.py
app/routers/masterdata/steel_mill.py
app/schemas/dto/steel_mill_dto.py
app/schemas/vo/steel_mill_vo.py
static/js/features/masterdata/steel-mill/{template,index}.js
```

导入和其它调用方只调钢厂 Service 的 §5.2。Router 不调钢厂 Repository。Parser 不调钢厂。核算热路径也不自己拼别名。

权限登记进 `catalog.json`。侧栏、`pageMeta` 与牌号分类同一层。

---

## 11. 评审清单

下列已在现网做到。

- [x] 维护页在主数据，菜单文案是 **钢厂**。顺序是基地、项目、供应商、牌号分类、钢厂
- [x] 主键是 `id`；一家可有多条别名，附属且 CASCADE。头表不 `relationship` 别名
- [x] 页面主字是缩写，全称用来对表头；页头说明与供应商相同
- [x] 停用后导入和下拉都不能再选；已落库的行保留
- [x] 「山钢」与「山钢(新)」收到同一个 `steel_mill_id`。基准价原文各自保留，全称列都是「山钢」
- [x] 只有本页能插入钢厂和别名。Parser 不调钢厂 Service
- [x] 基准价新写入：`steel_mill` 为 Excel 原文，另有 `canonical_steel_mill` 与 `steel_mill_id`
- [x] 加减价新写入带 `steel_mill_id`，`steel_mill` 写成全称
- [x] 钢厂不存在：整本退回，提示「请到钢厂页手工增加（#/steel-mill）」，不写库、不自动建档。多家顿号连在一句里，超过 20 家只列前 20 家
- [x] 已禁用：整本退回，提示到钢厂页启用
- [x] 基准价：同一文件两种写法收成同一家且业务键相撞，整本退回，不合并
- [x] 加减价：同一文件两张表页收到同一家钢厂，整本退回，不再要求业务键相撞。操作员看到改 Excel 或改钢厂档案两条处理
- [x] 对外解析一次装对照表，返回 `id`；基准价、加减价、中标厚度、钢材联动、LLM 问句都走 §5.2
- [x] 基价与政策的关联、唯一键使用 `steel_mill_id`。基准价列表、加减价列表主字是缩写
- [x] LLM 加减价异常比较按结果行上的 `steel_mill_id` 配对。问句里的钢厂在本结果表上收成 id，不调用钢厂 Service
- [x] 钢材联动结果带同一个 id；外键 `RESTRICT`。唯一键里的钢厂也是这个 id
- [x] 删除仍被引用的钢厂返回「仍被引用，不能删除」
- [x] `adjustment_common.py` 里靠猜钢厂的别名表、「(新)」自动互通和 `steel_mill_matches` 整段删除，不迁入 `app/common/`
- [x] 种子一次写入 §5.1 的全部缩写、全称和别名。表非空则跳过，不覆盖页面上后来加的别名
- [x] 三个库已对齐。基准价补了 id 和全称，原文不动；加减价别名行的 `steel_mill` 改成全称。鞍钢集团、TAGAL 折进鞍本。启动不再回填
- [x] 档案是这 12 家。鞍钢集团和 TAGAL 只是鞍本的别名。本钢仍是另一家。masterdata 不依赖一事一议和核算

§9 本期不做的仍然不做。

## 12. 已对齐

- [x] §6 拒绝句带上位置。基准价写出 Excel 行，加减价写出 sheet。同一原文只引用先出现的那一处
- [x] 冲压钢材联动价列表主字是缩写，筛选按 `steel_mill_id`。结果行上的 `steel_mill` 仍是计算当时的字
- [x] 中标钢厂厚度价格列表的钢厂列是缩写。配对仍按 `steel_mill_id`
- [x] LLM 加减价异常交给模型的钢厂字是结果行上的 `steel_mill`。配对键是 `steel_mill_id`。不读钢厂档案
