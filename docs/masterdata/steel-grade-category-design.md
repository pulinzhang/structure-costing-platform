# 牌号分类表 — 档案管理设计说明

> 状态：**已落地（MVP）**  
> 关联：`app/models/yishiyiyi/steel_base_price.py`、`app/models/stamping/part.py`、`docs/architecture.md`  
> 原则：一张标准档案，回答「这个牌号属于冷轧 / 镀锌 / 酸洗哪一类」。字段与基准价对齐：`category_name` + `grade`。**本表唯一键只有 `grade`**。**只有本切片手工 CRUD 写入**。工艺 `material`、基价 `grade` 外键 RESTRICT。表归绝对上游 `masterdata`。

---

## 0. 一句话

> **牌号分类表是牌号主数据：`grade` 是唯一键，全库一行；挂且只挂一个 `category_name`（冷轧 / 镀锌 / 酸洗）。档案只能在主数据页手工新增/编辑。新增/编辑落库只去空格并大写，不改字母 O。是否已存在：录入与库中 `grade` 都把 O/o 改成 0 再大写后比较。冲压工艺、基准价导入不往本表插行。基价新写入命中档案后落档案 `grade` 与档案大类。缺档整批拒绝。删除档案时若仍被零件或基价引用则 RESTRICT；档案改牌号 `ON UPDATE CASCADE`。**

不是核价公式，不是基价替代表。

对外、菜单、文档一律称 **牌号**，与基准价 `grade`（钢材牌号）同一口径。不要称「钢种分类」——基价里 `category_name` 只是大类，本表管的是牌号档案。

**谁用：** 一事一议和核算只读同一张表。基准价导入、冲压导入不再补档案。

---

## 1. 为什么做

现网两处各自写牌号，没有一张标准档案：

| 来源 | 字段 | 有没有大类 | 问题 |
|------|------|------------|------|
| 基准价格 `steel_base_prices` | `grade`（钢材牌号）+ `category_name`（大类） | 有。注释与现网取值就是 **镀锌、冷轧、酸洗** | 大类写在每一条月度基价行上，随年月/钢厂/规格重复；没有「全库牌号清单」 |
| 冲压零件 `stamping_parts` / 拼焊子片 `stamping_tailor_weld_blanks` | `material`（工艺卡「材质」，语义即牌号） | **没有** | 工艺卡只有牌号。核价时用档案把 `material` 收成大类，再对基价 `category_name` |

钢材联动现网：与中标钢厂厚度价格一览相同——只取当期基价表里出现的牌号及其自身基准价（`grade` 去空格后比对，字母 O 与数字 0 视为同一字符，按牌号+钢厂去重）。档案大类只用于厚度 CATEGORY 政策。落库仍带工艺牌号。零件核价按 `牌号 + 料厚` 取联动价。基价表没有的工艺牌号不输出。
档案把「牌号 ↔ 大类」从基价行上抽成可维护的主数据。

要管的四件事：

1. **查得见**：钢板 / 核价能打开一张表，按大类看有哪些牌号。  
2. **补得上**：缺档只能主数据页手工新增，不能靠导入偷偷插。  
3. **大类按基价现网写死三种**：`steel_base_prices.category_name` 去重只有 **`冷轧`、`镀锌`、`酸洗`**（见 §5.3）。政策里的「冷轧钢 / 镀锌钢 / 酸洗钢」是别名，写入档案时收到这三字；其它政策长文案不进档案。  
4. **两口共用一份**：一事一议和核算都按 `grade` 问大类，禁止各切一张副本。

---

## 2. 名词对照

与基准价同一套字段名。工艺表历史字段 `material` 不改，比对时当成 `grade`。

| 业务怎么说 | 本表字段 | 现网对应 | 含义 |
|------------|----------|----------|------|
| **大类** | `category_name` | `steel_base_prices.category_name` | 只允许：`冷轧` / `镀锌` / `酸洗` |
| **大类序号** | `category_seq` | 无（本表自管，基价没有） | 写死：冷轧=1、镀锌=2、酸洗=3。展示、排序用这个号，不按汉字 |
| **牌号** | `grade` | `steel_base_prices.grade`；零件/子片 `material` | 同一串，如 `DC01`、`DC51D+Z`、`HC340/590DP` |

写死：本表 `grade` ≡ `steel_base_prices.grade` ≡ `stamping_parts.material` ≡ `stamping_tailor_weld_blanks.material`。  
档案与基价都用 `grade`；零件侧继续叫 `material`（工艺卡原文）。

---

## 3. 定稿约定

| 约定 | 内容 |
|------|------|
| 表名 | **`steel_grade_categories`**（牌号分类档案） |
| 归属 | **`masterdata`**（必须）。一事一议和核算都要读；二者都是相对主数据的下游。禁止放 `costing`（一事一议不得依赖核算）。masterdata **不得**回调 yishiyiyi / stamping |
| 产品入口 | 主数据 → **牌号分类**（单页列表 + 抽屉增改，不拆上传/列表两套） |
| API | `/api/masterdata/steel-grade-category`（档案 CRUD）。核算 **不另做一套 API**，Service 内调 `SteelGradeCategoryService` |
| Hash | `#/steel-grade-category`（与基地 `#/location`、供应商 `#/supplier-list` 一样用功能名，不加 `masterdata` 前缀） |
| 权限 | `menu:steel-grade-category` 挂在 `menu:masterdata` 下；`op:…:view/create/update/delete/export`。码与 Hash 对齐功能名，不随包路径改字面量 |
| 唯一键 | **只有 `grade`**（去空格并大写后）。`UNIQUE (grade)`。**不是** `(category_name, grade)` |
| 大类 | `category_name` 是属性，不是键。写死 `("冷轧", "镀锌", "酸洗")`；必填，禁止空 |
| 大类序号 | **写死** 冷轧=1、镀锌=2、酸洗=3。列 `category_seq`，由 `category_name` 派生，禁止手填。列表/下拉/导出按 1→2→3 排 |
| 零件表 | `stamping_parts.material`、`stamping_tailor_weld_blanks.material` → `steel_grade_categories.grade`，删档 `RESTRICT`，档案改牌号 `CASCADE`；空材质不引用 |
| 基价表 | `steel_base_prices.grade` → 同一档案列，删档 `RESTRICT`，档案改牌号 `CASCADE`；行上仍保留 `category_name` |
| 读法 | 一事一议、核算都走本切片稳定查询（如 `get_by_grade` / `map_grades`）。**禁止**各切片直接 `query` 这张表绕过 Service（核算热路径可只读本切片 Repository） |
| 写 | **仅本切片 CRUD**。禁止下游插档。基价导入/手工创建：每条调用 `match_by_grade_key`，命中后落档案 `grade` 与档案 `category_name`。工艺导入仍 `require_existing_grades`（原文精确匹配）。缺档整批拒绝，进度区写明到「主数据 → 牌号分类」补档，不弹 Toast |

依赖（允许、单向、禁止成环）：

```text
写入
  主数据档案页  →  本切片 CRUD（唯一写入通道）

读取
  stamping / yishiyiyi / costing / dashboard
      →  masterdata.SteelGradeCategoryService（或只读 Repository）
      →  厚度加减价见 docs/yishiyiyi/thickness-policy-category-level-design.md

禁止
  masterdata → yishiyiyi / stamping / costing
  下游往 steel_grade_categories 插行
  costing 里再建一张牌号分类副本
```

**为什么必须放主数据：** 一事一议与核算都要读；主数据是绝对上游。放 costing = 上游读下游，禁止。

---

## 4. 与现网两张表的关系

```text
steel_base_prices                    steel_grade_categories                 stamping_parts / 子片
─────────────────                    ─────────────────────                 ────────────────────
category_name  ─┐                    category_name（必填：冷轧 / 镀锌 / 酸洗）
grade          ─┴── 只读对照 ──────►  grade     ◄── 只读对照 ────────  material（当牌号用）
year, month, location, mill, spec…   （无年月、无基地、无钢厂）            仍是零件行上的材质字符串
（价事实，每月可重复同一牌号）        （主数据，全库一行；手工维护）
```

| 问题 | 答案 |
|------|------|
| 档案要不要抄基价的年/月/基地/钢厂？ | **不要。** 分类与行情无关。 |
| 档案唯一键是不是 `(category_name, grade)`？ | **不是。唯一键只有 `grade`。** |
| 零件 `material` 改成外键？ | **要。** 指向档案 `grade`，删档 `RESTRICT`，档案改牌号 `CASCADE`。拼焊总成材质可空。 |
| 政策里的「冷轧钢」进不进档案？ | **不进第四种。** 手建时按 §5.3 别名收口成 `冷轧`。 |
| 导入缺档怎么办？ | **整批拒绝**，请先到主数据牌号分类补档。不自动插档。 |
| 基价表头写 DCO1 / 冷轧钢？ | **改写后落库。** `match_by_grade_key`（内部 `grade_match_key`：O→0 再大写）命中档案后落档案 `grade`（`DC01`）；钢种用档案大类。表头大类与档案不一致只警告。禁止把 `DCO1` 当新牌号补进档案。 |

---

## 5. 表结构：`steel_grade_categories`

### 5.1 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | |
| `category_name` | String(50) | ✓ | 与基价同名字段。只允许：`冷轧` / `镀锌` / `酸洗` |
| `category_seq` | Integer | ✓ | **展示序号。** 由 `category_name` 派生：冷轧=1、镀锌=2、酸洗=3 |
| `grade` | String(50) | ✓ | **唯一键。** 落库去空格、全部大写（`qste420tm` → `QSTE420TM`）。不把字母 O 改成数字 0。种子不灌 `DCO3`/`DCO4` |
| `remark` | Text | | 人工备注 |
| AuditUserMixin | | ✓ | |

**不建：** `year`、`month`、`location`、`steel_mill`、`thick`、`material`、英文 `category`、审核流。

### 5.2 约束

```text
PK:     id
UNIQUE: grade                            -- uix_steel_grade_category_grade
禁止:   UNIQUE (category_name, grade)
Index:  category_name / category_seq
```

查、核算取大类：一律按 `grade` 命中。  
SQLite 下 `grade` 比较按入库规范化后的字符串（去空格、全部大写；不改 O/0、不拆斜杠双牌号）。  
`B170P1/HC180Y` 与 `HC180Y` 是两行；互认仍走现网 `grades_match`。

### 5.3 大类合法值（按现网基价写死）

```python
# 与 steel_base_prices.category_name 现网取值逐字相同
CANONICAL_CATEGORIES: tuple[tuple[int, str], ...] = (
    (1, "冷轧"),
    (2, "镀锌"),
    (3, "酸洗"),
)
```

常量放 `app/common/steel_grade_category.py`（Parser 禁止依赖 masterdata）。

写入 `category_name` 的同时 **必须** 写入对应 `category_seq`。手建、编辑：下拉只给这三项，**禁止**存 `NULL`、禁止自由输入。别名收口：`冷轧钢`/`冷扎`→`冷轧`，`镀锌钢`→`镀锌`，`酸洗钢`→`酸洗`。其它文案 `BusinessException`，不新增大类。

---

## 6. 写入通道（仅手工）

| 操作 | 规则 |
|------|------|
| 新增 | `grade` + `category_name` 都必填。落库只去前后空格并全部大写，**不改字母 O**。是否已存在：录入与库中每一行都做「O/o→0 再大写」后比较，命中 → 409 |
| 编辑 | **与新增同一套。** 同一条 `apply_patch`，可改 `grade`、大类、备注。引用列靠外键 `ON UPDATE CASCADE`，禁止另写一套迁引用 |
| 删除 | 仍被工艺 `material` 或基价 `grade` 引用 → `仍被引用，不能删除` |
| 空库种子 | 无库 / 表为空时，启动写入现网牌号（`ensure_seed_if_empty`）。已有任意行则跳过。不灌 `DC01 HC180YD+Z`、不灌 `POLICY_TEST_*`、不灌 `DCO3`/`DCO4`（只灌 `DC03`/`DC04`） |

禁止：

- 基价导入 / 工艺导入往本表插行  
- 下游 Service 写本表  
- 有数据后再按种子覆盖大类

缺档：冲压工艺导入 `require_existing_grades`（原文）整批失败；基价导入/手工创建经 `match_by_grade_key` 仍找不到则同样失败。空材质（拼焊总成）不校验。
新增、编辑档案时去空格、大写后落库；查重按 `grade_match_key`（O→0 再大写）单行比较。不把 O 改成 0 写入。与已有行冲突 → 409。

---

## 7. 冲突

| 现象 | 处理 |
|------|------|
| 档案没有该牌号 | 先手工补档，再导入工艺/基价 |
| 同一牌号基价两种大类 | 档案以手填为准；不根据基价覆盖 |

核算若走本表取大类：缺档 = 该牌号缺大类（partial / 明细警告）。

---

## 8. 产品范围

### 8.1 本期做（MVP）

| 能力 | 说明 |
|------|------|
| 列表 | HUD 密表；默认 `ORDER BY category_seq, grade`；大类胶囊；牌号模糊搜；`page-size.js` |
| 新增 / 编辑 | 抽屉；大类三选一；序号不手填 |
| 删除 | 操作列按钮 |
| 导出 Excel | 当前筛选 |
| 空库种子 | 第一次启动、档案为空时写入现网牌号分类 |
| 权限 | `menu:steel-grade-category` + `op:…:view/create/update/delete/export` |

侧栏：主数据内，供应商之后。菜单文案写 **牌号分类**。

### 8.2 本期建议做、可薄

| 能力 | 说明 |
|------|------|
| 导入 Excel | 两列 `category_name`、`grade`；大类必填；已有则跳过或报行号，不要静默改大类 |

### 8.3 本期不做

| 非目标 | 原因 |
|--------|------|
| 改 `steel_base_prices` 唯一键 / 去掉行上 `category_name` | 价事实与档案分离 |
| 零件 `material` 外键或改名为 `grade` | 列名仍叫 `material`；外键已接到档案 `grade` |
| 导入自动插档 | 下游不允许插入 |
| 斜杠双牌号自动拆成两行 | 避免档案膨胀 |
| 审核流、文件溯源 | 手建不算上传原件 |
| 第四种大类、按基地分档案 | 与现网基价大类口径不一致 |

---

## 9. 垂直切片

```text
app/models/masterdata/steel_grade_category.py
app/repositories/masterdata/steel_grade_category/
app/services/masterdata/steel_grade_category/   # CRUD；外部匹配 match_by_grade_key
app/routers/masterdata/steel_grade_category/crud.py
app/common/steel_grade_category.py              # 大类常量；Parser 可读
app/schemas/dto/steel_grade_category_dto.py
app/schemas/vo/steel_grade_category_vo.py
static/js/features/masterdata/steel-grade-category/{template,index}.js
```

金额无关，无 `Decimal`。

---

## 10. 评审清单

- [x] 产品名是 **牌号分类**，字段与基价对齐：`category_name` + `grade`
- [x] **唯一键只有 `grade`**
- [x] 大类写死 **`冷轧`、`镀锌`、`酸洗`**，序号 **1 / 2 / 3**
- [x] 归属 **masterdata**；禁止放 costing；masterdata 不回调一事一议
- [x] 下游只读；缺档手工新增，导入不插档
- [x] 档案新增/编辑只去空格并大写；查重两边都 O→0 再大写；禁止第二套落库
- [x] 基价新写入落档案已有 `grade` + 档案 `category_name`
- [x] 核算单向读本切片
- [x] 零件 `material`、子片 `material`、基价 `grade` 外键指向档案；删档 RESTRICT；改牌号 CASCADE
