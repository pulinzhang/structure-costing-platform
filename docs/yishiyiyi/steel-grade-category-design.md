# 牌号分类表 — 档案管理设计说明

> 状态：**已落地（MVP）**  
> 关联：`app/models/yishiyiyi/steel_base_price.py`、`app/models/stamping/part.py`、`docs/architecture.md`  
> 原则：一张标准档案，回答「这个牌号属于冷轧 / 镀锌 / 酸洗哪一类」。字段与基准价对齐：`category_name` + `grade`。**本表唯一键只有 `grade`**（不是 `(category_name, grade)`）。基价导入、工艺导入都是：`grade` 档案里没有就插入，有则不动。基价行继续带自己的大类；不改零件表结构。一事一议与核算都要读这张表，所以表必须在上游 `yishiyiyi`。

---

## 0. 一句话

> **牌号分类表是牌号主数据：`grade` 是唯一键，全库一行；挂且只挂一个 `category_name`（冷轧 / 镀锌 / 酸洗）。基准价导入、冲压工艺导入都走同一套补行：档案里没有这个 `grade` 就插入，有则不改。基价插入时带上大类；工艺插入时大类能认出就填，认不出就待分类。**

不是核价公式，不是基价替代表，也不给 `stamping_parts.material` 加外键。

对外、菜单、文档一律称 **牌号**，与基准价 `grade`（钢材牌号）同一口径。不要称「钢种分类」——基价里 `category_name` 只是大类，本表管的是牌号档案。

**谁用：** 一事一议和核算读同一张表。基准价导入、冲压导入都只负责「缺 `grade` 就插入」，不是主消费者。

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
2. **补得上**：基准价导入、工艺导入，档案里没有这个 `grade` 就插入，不能丢牌号。  
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
| **待分类** | `category_name IS NULL` | 无 | 工艺导入新见到、基价里还对不上的牌号 |
| **档案来源** | `source` | 无 | 这一行最初是基价同步、工艺补录，还是页面手建 |

写死：本表 `grade` ≡ `steel_base_prices.grade` ≡ `stamping_parts.material` ≡ `stamping_tailor_weld_blanks.material`。  
档案与基价都用 `grade`；零件侧继续叫 `material`（工艺卡原文），导入时按牌号写入档案。

---

## 3. 定稿约定

| 约定 | 内容 |
|------|------|
| 表名 | **`steel_grade_categories`**（牌号分类档案） |
| 归属 | **`yishiyiyi`**（必须）。一事一议和核算都要读；核算是下游，可以调一事一议。若放 `costing`，一事一议读核算 = 上游依赖下游，禁止 |
| 产品入口 | 一事一议 → **牌号分类**（单页列表 + 抽屉增改，对齐废料价那种档案 CRUD，不拆上传/列表两套） |
| API | `/api/yishiyiyi/steel-grade-category`（档案 CRUD）。核算 **不另做一套 API**，Service 内调 `SteelGradeCategoryService` |
| 唯一键 | **只有 `grade`**（strip 后）。`UNIQUE (grade)`。**不是** `(category_name, grade)`：同一牌号不能在冷轧一行、镀锌再一行 |
| 大类 | `category_name` 是属性，不是键。写死 `("冷轧", "镀锌", "酸洗")`；手建 / 编辑必填；工艺自动插入允许空 |
| 大类序号 | **写死** 冷轧=1、镀锌=2、酸洗=3。列 `category_seq`，由 `category_name` 派生，禁止手填；待分类则为空。列表/下拉/导出按 1→2→3 排 |
| 零件表 | **不改** `stamping_parts` / 子片表结构；**不加 FK** |
| 基价表 | **不改** `steel_base_prices` 结构；行上仍保留 `category_name` + `grade`（月度价事实，继续进唯一键） |
| 读法 | 一事一议、核算都走本切片稳定查询（如 `get_by_grade` / `map_grades`）。**禁止**各切片直接 `query` 这张表绕过 Service（核算热路径可只读本切片 Repository，仍算下游→上游） |

依赖（允许、单向、禁止成环）：

```text
写入
  stamping 工艺上传  →  yishiyiyi.ensure_grades（缺 grade 则插入）
  yishiyiyi 基价导入 →  yishiyiyi.ensure_grades（缺 grade 则插入，带上大类）
  yishiyiyi 档案页   →  本切片 CRUD
  上线一次           →  对现网基价去重后调同一套 ensure_grades

读取（以后都要）
  yishiyiyi（政策匹配 / 中标厚度 / 按大类筛牌号）
      →  本切片 get_by_grade / map_grades
      →  厚度加减价（冷轧/镀锌/酸洗、分类级）见 docs/yishiyiyi/thickness-policy-category-level-design.md
  costing（钢材联动 / 零件核价 / 成品核价）
      →  yishiyiyi.SteelGradeCategoryService（或只读 Repository）

禁止
  yishiyiyi → stamping / costing
  costing 里再建一张牌号分类副本
```

**为什么不能放核算：** 一事一议要用。宪法只允许 `costing → yishiyiyi`，不允许 `yishiyiyi → costing`。主数据放下游，上游就读不到。

**为什么不能放冲压：** 一事一议就要同层依赖冲压；大类语义也不在工艺卡上。冲压只负责导入时补行。

---

## 4. 与现网两张表的关系

```text
steel_base_prices                    steel_grade_categories                 stamping_parts / 子片
─────────────────                    ─────────────────────                 ────────────────────
category_name  ─┐                    category_name（可空=待分类）
grade          ─┴── 去重 / 同步 ──►  grade     ◄── 工艺导入缺则插入 ──  material（当牌号用）
year, month, location, mill, spec…   （无年月、无基地、无钢厂）            仍是零件行上的材质字符串
（价事实，每月可重复同一牌号）        （主数据，全库一行）
```

| 问题 | 答案 |
|------|------|
| 档案要不要抄基价的年/月/基地/钢厂？ | **不要。** 分类与行情无关。`DC01` 今年在青岛、明年在芜湖都是冷轧。 |
| 档案唯一键是不是 `(category_name, grade)`？ | **不是。唯一键只有 `grade`。** 大类是这行的属性。基价表复合唯一键里带 `category_name`，那是月度价事实，不要抄到档案上。 |
| 零件 `material` 改成外键？ | **不要。** 工艺可空（拼焊总成）、历史行、删档案都不能把零件卡住。比对继续用字符串。 |
| 政策里的「冷轧钢」进不进档案？ | **不进第四种。** 同步基价时按 §6 别名收口成 `冷轧`。 |
| 为什么不叫钢种、不建 `material` 列？ | 与基准价对齐：管的是 **牌号** `grade`，大类仍是 `category_name`。 |

---

## 5. 表结构：`steel_grade_categories`

### 5.1 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | |
| `category_name` | String(50) | 手建必填；自动插入可空 | 与基价同名字段。标准大类：`冷轧` / `镀锌` / `酸洗`。空 = 待分类 |
| `category_seq` | Integer | 有大类则必填；待分类可空 | **展示序号。** 由 `category_name` 派生，禁止独立改：冷轧=1、镀锌=2、酸洗=3 |
| `grade` | String(50) | ✓ | **唯一键。** 与基价同名字段。钢材牌号，去首尾空白后全库一行。例：`DC01`、`DC51D+Z` |
| `source` | String(20) | ✓ | `base_price` / `stamping_upload` / `manual` |
| `remark` | Text | | 人工备注 |
| AuditUserMixin | | ✓ | `created_at` / `created_by` / `updated_at` / `updated_by` |

**不建：** `year`、`month`、`location`、`steel_mill`、`thick`、`material`（牌号只保留 `grade`，与基价同一列名）、英文 `category`、审核流（档案不是月度价，不走基价那套审核）。

### 5.2 约束

```text
PK:     id
UNIQUE: grade                            -- uix_steel_grade_category_grade
                                        -- 唯一键 = 牌号；一个 grade 全库一行
禁止:   UNIQUE (category_name, grade)    -- 那会允许同一牌号挂两个大类
禁止:   把 category_seq 当唯一键或复合键
Index:  category_name                    -- 按大类筛选
Index:  category_seq                     -- 列表按 1、2、3 排
Index:  source
```

查、插、补行、核算取大类：一律按 `grade` 命中，不要按大类+牌号复合键。  
SQLite 下 `grade` 比较按入库规范化后的字符串（strip，不改大小写、不拆斜杠双牌号）。  
`B170P1/HC180Y` 与 `HC180Y` 是两行（两个不同的唯一键）；互认仍走现网 `grades_match`，档案不当匹配引擎。

### 5.3 大类合法值（按现网基价写死）

不是猜的，是现网 `steel_base_prices.category_name` 去重后的全部取值（2026-08-26 主库）。序号与名称绑死，展示一律用号，不要按汉字排序：

```python
# 与 steel_base_prices.category_name 现网取值逐字相同，不要改成「冷轧钢」
# 序号只为展示 / 列表排序，不是唯一键
CANONICAL_CATEGORIES: tuple[tuple[int, str], ...] = (
    (1, "冷轧"),
    (2, "镀锌"),
    (3, "酸洗"),
)
CANONICAL_CATEGORY_NAMES: tuple[str, str, str] = ("冷轧", "镀锌", "酸洗")
CATEGORY_SEQ_BY_NAME: dict[str, int] = {"冷轧": 1, "镀锌": 2, "酸洗": 3}
```

| 序号 `category_seq` | `category_name` | 基价行数 |
|---------------------|-----------------|----------|
| **1** | `冷轧` | 641 |
| **2** | `镀锌` | 528 |
| **3** | `酸洗` | 184 |
| （空） | 待分类 | — |
| **合计（基价）** | | **1353** |
| 第四种 / 4 号 | **没有** | |

写入 `category_name` 的同时 **必须** 写入对应 `category_seq`（Service 查表，DTO 不收序号）。`category_name IS NULL` → `category_seq IS NULL`。禁止只改其中一个。

| 表 | 现网 `category_name` | 和本档案的关系 |
|----|----------------------|----------------|
| `steel_base_prices` | 只有上面三字 | **档案标准值 = 这三字** |
| `steel_prices`（核算结果） | 现网见过 `冷轧`、`镀锌`（酸洗视材料是否入算） | 读档案时仍只认这三字 |
| `steel_price_policies` | `冷轧钢` / `镀锌钢` / `酸洗钢`，另有锌层、卷板分组等长文案 | **不是**档案值。政策匹配继续用现网 `category_aliases`；写入档案前必须收到上面三字，收不了就拒绝 |

写入前规范化（同步基价、手建、Excel 导入共用同一纯函数，放 yishiyiyi 切片，与 `adjustment_common.category_aliases` 对齐）：

| 原文 | 写入档案 |
|------|----------|
| `冷轧`（基价原文） | `冷轧` |
| `镀锌`（基价原文） | `镀锌` |
| `酸洗`（基价原文） | `酸洗` |
| `冷轧钢` / `冷扎` | `冷轧` |
| `镀锌钢` | `镀锌` |
| `酸洗钢` | `酸洗` |
| 空 / 纯空白 | `NULL`（仅工艺自动插入允许） |
| 政策里的锌层/卷板长文案等其它 | 拒绝（`BusinessException`），不新增大类 |

手建、编辑、Excel 导入：下拉只给这三项，**禁止**存 `NULL`、禁止自由输入。只有工艺自动补行可以待分类。

基价同步：`category_name` 已是这三字则原样写入，不必再映射。若将来基价 Excel 出现第四种字，同步失败并报出，**改常量之前不得入库**。

---

## 6. 行从哪来（三条写入通道）

基准价导入和工艺导入走 **同一套** `ensure_grades`：按唯一键 `grade` 查，没有就插入，有就跳过。不要各写一份 SQL。

### 6.0 `ensure_grades`（共用）

```text
SteelGradeCategoryService.ensure_grades(
    db,
    items=[{"grade": "DC01", "category_name": "冷轧"}, ...],  # category_name 可省略
    source="base_price" | "stamping_upload",
    current_user=...,
)
```

| 档案里该 `grade` | 动作 |
|------------------|------|
| **没有** | **插入**一行（基价、工艺相同）。`grade` 必填；`category_name` 有合法值就写入，并带上对应 `category_seq`（1/2/3）；没有就两者都 `NULL`（待分类）；`source` 用本次调用的来源 |
| 已有 | **不插入、默认不改大类、不改序号、不改 source**（唯一键已命中） |
| 已有且大类为空、本次带了合法大类 | **补大类 + 序号**（待分类被认领）。基价导入常见；工艺导入通常补不上 |
| 已有且大类不同 | **不覆盖**；记冲突到本次导入结果，基价/工艺行本身仍入库 |

禁止因为档案缺行而拒绝整份基价导入或整份工艺导入。空 `grade` / 纯空白：跳过。

### 6.1 基准价导入时补行（与工艺相同：缺则插入）

触发点：基价 Import Service 写入 `steel_base_prices` 的 **同一事务内**，在基价行即将提交前。

收集范围：本批次解析出的基价行，`(trim(grade), 规范化(category_name))` 去重；`grade` 空则跳过。大类必须是写死的三字，否则该条不写入档案（基价行是否入库仍按基价自己的规则；第四种大类见 §5.3）。

```text
ensure_grades(
    db,
    items=[{"grade": row.grade, "category_name": row.category_name}, ...],
    source="base_price",
    current_user=...,
)
```

与工艺的差别只有一项：基价行上 **已有大类**，插入时一并带上，新行一般不是待分类。

上线：对现网 `steel_base_prices` 去重后调 **同一套** `ensure_grades`（幂等，已有 `grade` 不会再插）。不要另写 `sync_from_base_price_grades`。

同一批次里同一 `grade` 出现两种大类：插入用第一次合法大类，其余记冲突。

### 6.2 冲压工艺导入时补行（相同：缺则插入）

触发点：`StampingUploadService.process_upload` 写入零件 / 拼焊子片的 **同一事务内**。

收集范围（去空白、去空、去重；零件字段仍是 `material`，当作 `grade`）：

- 普通件：`StampingPart.material`
- 拼焊子片：`StampingTailorWeldBlank.material`
- 拼焊总成父件材质可空，**不要**用空串插入档案

```text
ensure_grades(
    db,
    items=[{"grade": "DC01"}, {"grade": "DC51D+Z"}, ...],  # 无 category_name
    source="stamping_upload",
    current_user=...,
)
```

工艺卡没有大类。插入时若能在 **当前库基价** 按该 `grade` 查到规范化大类就带上；查不到就待分类。

禁止：

- 在 stamping Repository 里写牌号分类表 SQL（必须走 yishiyiyi Service）  
- 根据牌号后缀（`+Z` 等）猜镀锌

### 6.3 档案页手建 / 编辑 / 删除

对齐废料价那种主数据 CRUD，不要走「上传 Excel 覆盖整月」的基价模式（档案可以另做 **导入/导出** 作批量维护，见 §8）。

| 操作 | 规则 |
|------|------|
| 新增 | `grade` + `category_name` 都必填；`source=manual`；牌号冲突 → `BusinessException` |
| 编辑 | 可改大类、备注；**默认不改 `grade`**（改牌号等于换一条主数据，容易和零件对不上）。若产品坚持可改牌号，须校验新键不冲突 |
| 删除 | 仅删档案行，**不级联**零件、基价。已被零件或基价引用的牌号：允许删（档案不是 FK 父表），列表可用「引用中」提示，但不拦死 |

「引用中」是查询提示（零件/子片/基价是否出现过该字符串），不是数据库约束。

---

## 7. 冲突与待分类

| 现象 | 处理 |
|------|------|
| 工艺先到、基价后到 | 先待分类；基价同步时按 §6.1.2 补大类 |
| 基价先到、工艺后到 | `ensure_grades` 命中已有行，不插入 |
| 同一牌号基价两种大类 | 不覆盖已填档案；导入/同步结果里列冲突，人在档案页选定一种 |
| 待分类长期空着 | 档案页用筛选「待分类」让钢板补。核算若已改走档案取大类：待分类 = 该牌号缺大类（partial / 明细警告），**不**用空大类去改基价行 |

MVP 落地档案 CRUD 与补行时，核算仍可暂时从基价行抄大类（与现网一致）。一旦核算切到本表，待分类必须当缺数据，不能 silently 当冷轧。一事一议侧（政策大类 ↔ 牌号）同样只认已填的 `category_name`。

---

## 8. 产品范围

### 8.1 本期做（MVP）

| 能力 | 说明 |
|------|------|
| 列表 | HUD 密表；默认 `ORDER BY category_seq, grade`（1 冷轧 → 2 镀锌 → 3 酸洗，待分类排最后）；大类 Tab/胶囊按序号 1/2/3；牌号模糊搜；分页用 `page-size.js` |
| 新增 / 编辑 | 抽屉；大类三选一（展示「1 冷轧 / 2 镀锌 / 3 酸洗」）；序号不手填，保存时由 Service 写入 |
| 删除 | 操作列按钮，禁止整行点击进编辑 |
| 基价导入补行 | 与工艺相同：缺 `grade` 则 `ensure_grades` 插入，见 §6.1 |
| 工艺导入补行 | 缺 `grade` 则 `ensure_grades` 插入，见 §6.2 |
| 上线回填 | 现网基价去重后调同一套 `ensure_grades` |
| 权限 | `menu:steel-grade-category` + `op:…:view/create/update/delete`（可加 `export`） |

侧栏：一事一议内，建议放在 **基准价格** 与 **中标钢厂厚度价格一览表** 之间（先有牌号档案，再看基价/厚度表）。菜单文案写 **牌号分类**，不要写「钢种」。

### 8.2 本期建议做、可薄

| 能力 | 说明 |
|------|------|
| 导出 Excel | 当前筛选结果；含 `category_seq`、`category_name`、`grade` |
| 导入 Excel | 两列与基价对齐：`category_name`、`grade`（序号不导入，由名称派生）；大类必填；冲突按「已有则跳过或报行号」写进结果 VO，不要静默改大类 |

### 8.3 本期不做

| 非目标 | 原因 |
|--------|------|
| 改 `steel_base_prices` 唯一键 / 去掉行上 `category_name` | 价事实与档案分离；下一期再说 |
| 零件 `material` 外键或改名为 `grade` | 工艺表结构不动；档案侧与基价对齐即可 |
| 核算 / 一事一议 **立刻**改走档案取大类 | 档案未填满会算崩；先有表、有同步、有待分类可补，再切读取路径 |
| 斜杠双牌号自动拆成两行 | 与 `grades_match` 正交，避免档案膨胀 |
| 审核流、文件溯源 | 无独立业务 Excel 原件；手建不算上传原件 |
| 第四种大类、按基地分档案 | 与现网基价大类口径不一致 |

---

## 9. 垂直切片与落地清单

```text
app/models/yishiyiyi/steel_grade_category.py
app/repositories/yishiyiyi/steel_grade_category/
app/services/yishiyiyi/steel_grade_category/   # CRUD + ensure_grades + get_by_grade / map_grades
app/routers/yishiyiyi/steel_grade_category/crud.py
app/schemas/dto/steel_grade_category_dto.py
app/schemas/vo/steel_grade_category_vo.py
static/js/features/yishiyiyi/steel-grade-category/{template,index}.js
```

| # | 动作 |
|---|------|
| 1 | Model + 注册 `app/models/yishiyiyi/__init__.py`、`app/models/__init__.py` |
| 2 | Repository：按 `grade` 查、分页、批量 `in_`、插入 |
| 3 | Service：规范化大类、CRUD、**共用 `ensure_grades`**、`get_by_grade` / `map_grades` |
| 4 | Router：`ApiResponse` / `PageResult`；`require_perm(Perm.*)` |
| 5 | **基价导入** Service 同一事务内调 `ensure_grades`（缺 `grade` 则插入，带大类） |
| 6 | **工艺导入** `process_upload` 同一事务内调 `ensure_grades`（零件/子片 `material` 当牌号） |
| 7 | 权限目录 + `generate_perm_codes` + 侧栏 **牌号分类** + `pageMeta` + `app.js` |
| 8 | 上线：现网基价去重后调同一套 `ensure_grades` |
| 9 | 测试：基价缺牌号插入、工艺缺牌号插入、已存在不覆盖、大类冲突不覆盖、子片牌号、空牌号跳过 |

金额无关，无 `Decimal`。`grade` / `category_name` 按字符串规范化，VO 无需金额序列化。

---

## 10. 评审清单

- [ ] 同意产品名是 **牌号分类**（不要「钢种」），字段与基价对齐：`category_name` + `grade`
- [ ] 同意 **唯一键只有 `grade`**：`UNIQUE (grade)`；禁止 `(category_name, grade)` 复合唯一
- [ ] 同意大类写死为现网基价三字 **`冷轧`、`镀锌`、`酸洗`**，序号写死 **1 / 2 / 3**；展示、排序用序号；政策「×钢」写入时收口；第四种先报错再改常量
- [ ] 同意归属 **yishiyiyi**（一事一议与核算都要读；禁止放 `costing`）
- [ ] 同意基准价导入、冲压导入都调 **同一套** `ensure_grades`：`grade` 不存在则插入，存在则不改
- [ ] 同意缺档 **不拒绝** 整份基价/工艺导入；工艺认不出大类则待分类；基价插入带上大类
- [ ] 同意核算 **单向** 读本切片查询 API
- [ ] 同意 **不改** 零件表 / 基价表结构，不加 FK
- [ ] 同意核算切到本表取大类是 **下一刀**，不是另建副本
- [ ] 同意已有档案大类与基价不一致时 **不覆盖**，只报冲突
