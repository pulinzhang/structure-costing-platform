# 材料变更 — 2 上传与门禁

> 落地：**第二刀。** 业务门禁的唯一数据源是工作表 **「工程变更单（材质）」**。  
> 依赖：[01-tables-resolver.md](01-tables-resolver.md)。  
> 样表即规格：[samples/t13j-2026-06-material-change.xlsx](samples/t13j-2026-06-material-change.xlsx)（第一刀）；再变回去：[samples/t13j-2026-07-material-change.xlsx](samples/t13j-2026-07-material-change.xlsx)  
> 目录：[README.md](README.md)

指挥家：prepare（**先验这张表，再对库**）→ persist → commit。一条不过：**整本拒**，不插切点。禁止修格子、禁止跳过坏行、禁止 `workbook.active` 顶替表名。

文案前缀 `ECM_*`。报错必须带 **表名 + 第几行 + 列名**（能定位到格的），并写出这一格现在是什么、要改成什么。

---

## 0. 验什么、不验什么

| 对象 | 怎么验 |
|------|--------|
| 文件 | 只收 `.xlsx` |
| 表名 | 必须有且仅有：`材料变更填写说明`、`工程变更单（材质）`。差一个字就拒 |
| `材料变更填写说明` | **只认表名存在。** 不读格子、不互校、不当数据 |
| **`工程变更单（材质）`** | **整张严格验证。** 下面 §1–§5 全是这张表 |
| 上传页基地/项目/年/月 | 与这张表逐格全等（§3） |
| 工艺 / **最新解析材料** / 材料档案 / 供应商 / 已有切点 / 设计变更 | 这张表每一数据行对库（§4）。变更前必须对齐最新解析 |

禁止：按「工程变更单」去读设计变更那张表；禁止表名模糊包含「材质」就算；禁止抽其它表。

---

## 1. 表形（打开「工程变更单（材质）」立刻验）

常量（与样表全等，落地写死，禁止配置化改字）：

```
SHEET = 工程变更单（材质）
HEADERS = (基地, 项目, 变更版本, 生效年月, 冲压工厂, 零件号, 零件名称, 变更前材料, 变更前料厚, 变更后材料, 变更后料厚, 互换性)
```

十二列，A→L，**第 1 行就是表头**。不要在前 20 行里找表头。第 1 行十二个格子的字必须与 `HEADERS` 逐格全等（含顿号、括号）。

然后：

1. 工作表必须可见（hidden / veryHidden 拒）。
2. **禁止合并单元格**（本表 `merged_cells` 非空即拒）。不要学设计变更单去解合并。
3. **禁止公式**（任一格 `data_type == 'f'` 或 value 以 `=` 开头）。
4. **禁止图**（本表不得有 `_images`）。
5. **禁止表头以外的已用格。** 已用范围必须落在 `A1:L{1+N}`：M 列及以后有值拒；第 `2+N` 行及以下有值拒；第 1 行 M 列有值也拒。
6. 表头下至少一行数据。从第 2 行起连续 N 行（N≥1），每行 A–L 十二格都有值。
7. **禁止中间空行。** 第 k 行十格全空，且后面还有非空行 → 拒。连续数据读完后遇到全空行 = 结束；结束之后再出现非空 → 拒。
8. 本表不得重复零件号（列「零件号」全等）。

读格子：**不要 `strip` 后当成功。** 展示字必须等于库/常量；若 `text != text.strip()`（前后空白、换行、全角空格）→ 该格失败。不要 `upper()`。除「生效年月」外，不要把 Excel 日期序列当成年月或零件号。除料厚外，A–L 数据格必须是字符串（`s` / `inlineStr`）；数字、日期、布尔、空拒。**「生效年月」例外：** 文字「2026年6月」或「2026年06月」，或 Excel 日期（取年、月，日忽略）。**料厚两列只收数字**，大于 0，最多两位小数（`1`、`1.5`、`1.55` 可以，文字「1.5」、`1.555`、`0` 拒）。

---

## 2. 逐格格式（料厚收数字，其余认字符串）

对每一数据行、每一列，先通过再进入下一列。样表两行必须全部通过。

| 列 | 正则 / 枚举 | 失败码 |
|----|-------------|--------|
| 基地 | 非空字符串；整本同一字 | `ECM_LOCATION_MISMATCH` |
| 项目 | 非空字符串；整本同一字 | `ECM_PROJECT_MISMATCH` |
| 变更版本 | `^MAT-\d{6}$` | `ECM_VERSION_FORMAT` |
| 生效年月 | 文字「2026年6月」或「2026年06月」（月 1–12），或 Excel 日期（取年、月） | `ECM_EFFECTIVE_FORMAT` |
| 冲压工厂 | 非空字符串；整本同一字 | `ECM_SUPPLIER_MISMATCH` |
| 零件号 | 非空；本本不重复 | `ECM_DUPLICATE_CUTOVER` |
| 零件名称 | 非空 | `ECM_CELL_NOT_EXACT` |
| 变更前材料 | 非空；对库时必须 = **最新解析**（§4.1） | `ECM_BEFORE_MATERIAL` |
| 变更前料厚 | 数字格；大于 0；最多两位小数；对库时 Decimal 必须 = 工艺 `thickness` | `ECM_THICKNESS_FORMAT` / `ECM_BEFORE_THICKNESS` |
| 变更后材料 | 非空；**≠** 变更前（同一行字符串全等则不是换） | `ECM_AFTER_EQUALS_BEFORE` |
| 变更后料厚 | 数字格；大于 0；最多两位小数；相对变更前 |后-前|/前 **> 20%** 拒 | `ECM_THICKNESS_FORMAT` / `ECM_THICKNESS_DELTA` |
| 互换性 | 只准 `不影响互换性` 六个字 | `ECM_INTERCHANGE_REQUIRED` |

整本交叉（表还没对库）：

- 十二列里「基地 / 项目 / 变更版本 / 生效年月 / 冲压工厂」五行必须整本一个字。多值 → 对应 mismatch / version。
- `MAT-` 后面六位必须等于该本生效年月的 `YYYYMM`。样表：`MAT-202506` 配 `2025年06月`。`MAT-202507` 配 06 月 → `ECM_VERSION_FORMAT`。
- 版本空或本本多个版本 → `ECM_VERSION_REQUIRED`。

---

## 3. 对上传页（仍是这张表）

上传页四格：基地、项目、年、月。

| 上传页 | 表 |
|--------|----|
| 基地 | 列「基地」 |
| 项目 | 列「项目」（禁止 `upper()` 后相等） |
| 年、月 | 列「生效年月」拆出的四位年 + 两位月。`2025` 和 `6` 对不上 `2025年06月` 的月（页上月份必须是 6，值相等；**表里仍必须写 06**） |

对不上 → `ECM_LOCATION_MISMATCH` / `ECM_PROJECT_MISMATCH` / `ECM_EFFECTIVE_MISMATCH`。

样表上传页必须是 **芜湖 / T13J / 2025 / 06**。

---

## 4. 对库（每一数据行，按行号）

查工艺：`(location=基地, stamping_supplier=冲压工厂, vehicle_model=项目, part_number=零件号)` 且切点月 `is_in_period`（与零件列表 as_of **同一把钥匙**：`period_hit_clause` / 生失效四列）。找不到 → `ECM_PART_NOT_AS_OF`（**该月已停号或从未有过该月工艺**）。找到了再验：

| 条件 | 码 |
|------|----|
| 工艺 `location` ≠ 本行基地 | `ECM_LOCATION_MISMATCH` |
| 工艺 `vehicle_model` ≠ 本行项目 | `ECM_PROJECT_MISMATCH` |
| 工艺 `stamping_supplier` ≠ 本行冲压工厂 | `ECM_SUPPLIER_MISMATCH` |
| 供应商主数据没有这句规范全称 | `ECM_SUPPLIER_UNKNOWN` |
| 工艺 `part_name` ≠ 本行零件名称 | `ECM_PART_NAME` |
| `is_tailor_welded` | `ECM_TAILOR_WELD_FORBIDDEN` |
| `is_offal_nested` | `ECM_OFFAL_FORBIDDEN` |
| `is_scrap_byproduct` | `ECM_BYPRODUCT_FORBIDDEN` |
| 切点月早于工艺生效月 | `ECM_EFFECTIVE_TOO_EARLY` |
| 生效月项目 `require_introducible` 不过 | `ECM_PROJECT_PERIOD` |
| 工艺生效月等于本本切点月（见 §4.2） | `ECM_MIXED_WITH_REVISE` |
| 该号已有切点，且工艺 `material` ≠ 最早一刀 `before_material`（见 §4.4） | `ECM_PROCESS_MATERIAL_CHANGED` |
| 该身份已有切点，且本本生效月不晚于最晚切点 | `ECM_CUTOVER_NOT_LATER` |
| 变更前不在材料档案（全等） | `ECM_BEFORE_MATERIAL_UNKNOWN` |
| 变更后不在材料档案（全等） | `ECM_AFTER_MATERIAL_UNKNOWN` |
| 变更前 ≠ **该行身份在本本生效月、不含本本** 的解析值（库里最新材料） | `ECM_BEFORE_MATERIAL` |
| 变更前料厚 Decimal ≠ 工艺 `thickness`（同精度 4 位） | `ECM_BEFORE_THICKNESS` |
| 变更前料厚 ≤ 0 | `ECM_THICKNESS_FORMAT` |
| 变更后料厚 Decimal ≤ 0 | `ECM_THICKNESS_FORMAT` |
| \|变更后料厚 - 变更前料厚\| / 变更前料厚 **> 0.20** | `ECM_THICKNESS_DELTA` |

### 4.1 变更前 = 库里最新（硬门，再变靠它）

**变过以后还可以再变**，但变更前不准抄工艺表投产列，除非最新解析碰巧就是那一列。

对每一数据行：

```
expected_before = 冲压服务按该零件历史叠出的当月材料（无历史 = 工艺列）
# 本本尚未 persist，历史里还没有这一本
if 格子.变更前材料 != expected_before:
    拒 ECM_BEFORE_MATERIAL
```

文案必须写出格子是什么、库里最新是什么。禁止写成「请对照工艺表」。

| 时刻 | 115AA 库里最新 | 变更前格子 | 变更后 | 结果 |
|------|----------------|------------|--------|------|
| 尚未切过，本本 2025年06月 | `DC01` | `DC01` | `DC03` | 过（06 样表） |
| 尚未切过，本本 2025年06月 | `DC01` | `DC03` | 任意 | `ECM_BEFORE_MATERIAL` |
| 已有 `MAT-202506`，07 样表 | `DC03` | `DC03` | `DC01` | 过（再变回去） |
| 已有 `MAT-202506`，07 月仍写 DC01→DC03 | `DC03` | `DC01` | `DC03` | `ECM_BEFORE_MATERIAL`（工艺列不是最新） |
| 已有 `MAT-202506`，再传 06 月 | — | — | — | `ECM_CUTOVER_NOT_LATER` / 版本占用 |
| 没有 06 月、直接传 07 样表 | `DC01` | `DC03` | `DC01` | `ECM_BEFORE_MATERIAL`（最新仍是投产 DC01） |

07 样表必须 **先有 06 月成功头**。直接传 07 不是再变。再变 = 另起一本 + 更晚月 + 变更前对齐最新 + 变更后换一个档案材料（可以变回去）。同一本里同一零件写两行不是再变。

料厚：样表 115/116 变更前、变更后都是 `1.5`（与工艺料厚全等，差 0）。**本通道不改工艺 `thickness`**，变更后料厚只验、切点落库给人看。`list_materials_as_of` 只叠材料，不叠料厚。超过 ±20% 一定是填错。

```
before_t = Decimal(格子.变更前料厚)
after_t = Decimal(格子.变更后料厚)
if before_t != 工艺.thickness: 拒 ECM_BEFORE_THICKNESS
if before_t <= 0 or after_t <= 0: 拒 ECM_THICKNESS_FORMAT
if abs(after_t - before_t) / before_t > Decimal("0.20"): 拒 ECM_THICKNESS_DELTA
```

恰好 20% 过；大于 20% 拒。

### 4.2 与改图同一生效月（`ECM_MIXED_WITH_REVISE`）

不查设计变更单。只问冲压：该号 `effective_year` / `effective_month` 是否等于本本切点月。相等 → 整本拒。改图新号的生效月就是改图那个月，所以同月改材料会撞上。早于工艺生效月走 `ECM_EFFECTIVE_TOO_EARLY`，不走本条。

同号不同月不拒（新号下月可再切材料）。切点月工艺已到期 = 已停号，走 `ECM_PART_NOT_AS_OF`。T13J 06 样表 115/116 的工艺生效月不是 06 月，不撞 §4.2。

拼焊 / 利废 / 副产品：格子写了 DC01→DC03 也拒。

不拒：基价暂时没有新材料。

### 4.3 停号只认该月工艺有效（现网材料列表按月是错的）

**停号不是去翻设计变更单。** 改图 persist 已经把旧号工艺写到生效月的前一月到期。该月还在不在期内，只问生失效四列 / `is_in_period`（与 `#/stamping-parts` as_of 同一把钥匙）。

| 切点月对该号 | 材料变更 |
|--------------|----------|
| `is_in_period` 真 | 号还活着，继续后面的门 |
| `is_in_period` 假 | **该月已停号** → `ECM_PART_NOT_AS_OF` |

禁止再做：按设计变更单 `change_type=改图` 去翻整段历史（会把旧号最后几个仍有效月也误拦）。完成停止 / 此件不装本来就不停工艺行。停号与同月改图都只认生失效四列。

例：T13J 05 月改图 `551003095AA` 用到 04 月到期，新号 `551003095AB` 从 05 月生效。06 月材料变更写 `551003095AA` → `ECM_PART_NOT_AS_OF`。04 月仍有效，不因「库里有过改图」去拒。05 月写新号 `551003095AB` → 工艺生效月等于切点月 → `ECM_MIXED_WITH_REVISE`。

钢价 Step1 现网不按月、已停号仍进规格：第 4 刀改，见 [04-steel-and-part-cost.md](04-steel-and-part-cost.md) §1。本通道上传门禁不靠扫变更单剔停号。

### 4.4 SOP 改了投产材料：再切拒绝，先删旧切点再切

该身份（基地+厂+项目+零件号）**已经有成功切点**，且工艺行 `material` **全等不等于** 该号最早一刀的 `before_material`（投产字已被 SOP 改掉）→ `ECM_PROCESS_MATERIAL_CHANGED`，整本拒。

必须：先回滚，把该号旧切点删光，再按 **新的** 工艺 `material` 当变更前重新切。禁止在旧刀上继续叠。

没有切点时（含刚回滚完）：变更前 = 现在的工艺列，这是第一次切，不走本条。

头级（对整本，不是某一格）：

| 条件 | 码 |
|------|----|
| 该基地该项目该厂这个 `MAT-YYYYMM` 已有成功头 | `ECM_VERSION_DUPLICATE` |
| 已有 `pending` 头 | `ECM_PENDING_VERSION` |

回滚（第 3 刀）：`ECM_ROLLBACK_BLOCKED`。

---

## 5. 验表顺序（落地必须按这次序，先形后义）

对 `file.xlsx`：

1. 扩展名 `.xlsx`，否则 `ECM_FILE_TYPE`。
2. 打开后 `sheetnames` **恰好且按序** 为 `材料变更填写说明`、`工程变更单（材质）`（与样表一致）。多表、缺表、顺序反、别名 → `ECM_SHEET_REQUIRED`。
3. 取 **`工程变更单（材质）`**。可见、无合并、无公式、无图 → 否则 `ECM_MERGED` / `ECM_FORMULA` / `ECM_SHEET_IMAGE`。
4. 第 1 行 A–L = `HEADERS`；已用格不超出 `A1:L{1+N}` → 否则 `ECM_HEADER` / `ECM_EXTRA_CELL`。
5. 扫描第 2 行起：空表、中间空行、非字符串、首尾空白 → `ECM_EMPTY_ROW` / `ECM_CELL_TYPE` / `ECM_CELL_NOT_EXACT`。
6. 逐列正则 + 整本一个基地/项目/版本/月/厂 + 版本六位=年月 + 零件号不重复。
7. §3 对上传页。
8. §4 对库：先头级版本占用（含厂）；再逐行切点月工艺；再 §4.4 SOP 漂移；再 §4.2 同月；**再算最新解析，变更前必须全等**；再验料厚（前=工艺、后相对前不超过 20%）。

一步失败即停，不要凑合出半本切点。

---

## 6. 文案字典（常量值就是中文句，测试按全文匹配）

落地：本通道包内常量（不要写进 `engineering_change_gates.py`，不要塞 `app/common/`）。报错：`{常量}。工程变更单（材质）第 {n} 行「{列名}」写成…，请改成…`（整本级无行号则只补怎么改）。

| 常量 | 中文 |
|------|------|
| `ECM_FILE_TYPE` | 请另存为 .xlsx 再传，别的格式收不了 |
| `ECM_SHEET_REQUIRED` | 请只留两张表，表名必须是「材料变更填写说明」和「工程变更单（材质）」，顺序也要一样 |
| `ECM_HEADER` | 请把第 1 行改成样表那十二个列名，不要在上面再加标题 |
| `ECM_EXTRA_CELL` | 请删掉十二列以外、以及最后一行零件下面多出来的字 |
| `ECM_MERGED` | 请取消合并单元格后再传 |
| `ECM_FORMULA` | 请把公式换成算好的文字再传 |
| `ECM_SHEET_IMAGE` | 请删掉贴在表上的图片再传 |
| `ECM_EMPTY_ROW` | 请从第 2 行起把零件连续写完，中间不要空一行，表也不能是空的 |
| `ECM_CELL_TYPE` | 请把这一格改成文字。数字和日期都不认 |
| `ECM_CELL_NOT_EXACT` | 请去掉这一格的前后空格和换行，空着也不能传 |
| `ECM_EFFECTIVE_FORMAT` | 请把生效年月写成「2026年6月」或「2026年06月」，也可以直接选成日期 |
| `ECM_VERSION_FORMAT` | 请把变更版本写成 MAT- 加六位数字，并且和生效年月对上。2026年06月就写 MAT-202606 |
| `ECM_VERSION_REQUIRED` | 请整本只写一个变更版本，这一格不能空 |
| `ECM_VERSION_DUPLICATE` | 这个版本已经传过了。请换一个更晚的月份，或先到列表里删掉原来那本 |
| `ECM_PENDING_VERSION` | 这个版本正在导入，请等这次结束 |
| `ECM_EFFECTIVE_MISMATCH` | 请把生效年月改成和上传页同一个月。一本只能一个月 |
| `ECM_PROJECT_PERIOD` | 这个月这个项目还不能做材料变更 |
| `ECM_PART_NOT_AS_OF` | 这个零件在这个月没有还能用的工艺。请核对零件号，或改到它还在用的月份 |
| `ECM_EFFECTIVE_TOO_EARLY` | 请把生效年月改到工艺开始之后。工艺刚投产的那个月不能改材料 |
| `ECM_CUTOVER_NOT_LATER` | 这个零件已经有材料变更到这个月或更晚。请改到更晚的月份再传 |
| `ECM_MIXED_WITH_REVISE` | 这个零件这个月已经有设计变更。请换一个月再改材料 |
| `ECM_TAILOR_WELD_FORBIDDEN` | 拼焊件不能改材料。请把这一行删掉 |
| `ECM_OFFAL_FORBIDDEN` | 利废件不能改材料。请把这一行删掉 |
| `ECM_BYPRODUCT_FORBIDDEN` | 废料副产品不能改材料。请把这一行删掉 |
| `ECM_AFTER_EQUALS_BEFORE` | 变更前和变更后材料写成一样了。请把变更后改成要换成的牌号 |
| `ECM_AFTER_MATERIAL_UNKNOWN` | 变更后材料在材料档案里没有。请改成档案里已有的牌号，字要完全一样 |
| `ECM_BEFORE_MATERIAL_UNKNOWN` | 变更前材料在材料档案里没有。请改成档案里已有的牌号，字要完全一样 |
| `ECM_BEFORE_MATERIAL` | 变更前材料要写成这个月系统里正在用的牌号 |
| `ECM_BEFORE_THICKNESS` | 变更前料厚要写成工艺上的料厚 |
| `ECM_THICKNESS_FORMAT` | 请把料厚填成大于 0 的数字，最多两位小数，例如 1.5。不要写成文字 |
| `ECM_THICKNESS_DELTA` | 变更后料厚和变更前差得太多，超过两成了。请改近一些再传 |
| `ECM_PROCESS_MATERIAL_CHANGED` | 工艺上的材料被改过，和已有的材料变更对不上。请先到列表删掉这个零件已有的材料变更，再重新传 |
| `ECM_LOCATION_MISMATCH` | 基地要和上传页、工艺写成同一个字。一本只能一个基地 |
| `ECM_PROJECT_MISMATCH` | 项目要和上传页、工艺写成同一个字。一本只能一个项目 |
| `ECM_SUPPLIER_UNKNOWN` | 冲压工厂请写成供应商档案里的全称，简称不行 |
| `ECM_SUPPLIER_MISMATCH` | 冲压工厂要和工艺上的全称一样。一本只能一个厂 |
| `ECM_PART_NAME` | 零件名称要和工艺上完全一样 |
| `ECM_INTERCHANGE_REQUIRED` | 互换性请写成「不影响互换性」这六个字 |
| `ECM_DUPLICATE_CUTOVER` | 同一个零件写了两行。请删掉重复的那一行 |
| `ECM_ROLLBACK_BLOCKED` | 这个零件后面还有更晚的材料变更。请先到列表删掉更晚的那本，再删这一本 |

---

## 7. 上传壳（本刀落地）

指挥家文件：`app/services/engineering_change/material_change/upload/orchestrator/orchestrator.py`（主方法 ≤20 行：prepare → persist）。

| 项 | 规定 |
|----|------|
| 任务类型 | `engineering_change_material_upload`（新常量，禁止复用 `engineering_change_upload`） |
| 模板 | `GET /api/engineering-change/material/template`，文件名 `材料变更导入模板.xlsx`，表形与样表相同、无数据行 |
| 上传 | `POST /api/engineering-change/material/upload` Form：location、vehicle_model、effective_year、effective_month、file |
| 进度 | `GET /api/engineering-change/material/upload/tasks/{task_id}` |
| 文件大小 | 与现网工程变更上传同一上限 |
| 原件 | 入队落盘；失败头也能从本通道下载当时那份表。模板下载不落业务头。不改 file_trace |
| 失败头 | 事务回滚切点后把头标 failed，列表看得到；原件是否落盘失败路径跟现网设计变更同一纪律 |

---

## 8. 本刀验收（都冲着「工程变更单（材质）」）

对照样表，上传页芜湖 / T13J / 2025 / 06：

- [ ] 样表两行过门禁；模板下载无数据行、十二列与样表同形
- [ ] 改表名为「工程变更单」→ `ECM_SHEET_REQUIRED`（不要落到设计变更解析）
- [ ] 表头改成第 2 行、第 1 行写标题 → `ECM_HEADER`
- [ ] 合并「项目」列、M 列写备注、第 4 行空第 5 行再写、零件号做成数字、`2026年13月`、`MAT-202607`、DC01→DC01、互换性多空格、变更后料厚改 `2.0`：全部整本拒、零切点
- [ ] 再传同一 `MAT-202506` 拒
- [ ] 06 成功后直接传 07 样表过：变更前 DC03、变更后 DC01；06 成功后把 07 的变更前改成 DC01 → `ECM_BEFORE_MATERIAL`
- [ ] 不传 06、只传 07 样表 → `ECM_BEFORE_MATERIAL`（最新仍是 DC01）
- [ ] 与 2025年05月设计变更改图件不是 115/116，样表不撞 `ECM_MIXED_WITH_REVISE`
- [ ] 库里已有 05 月改图后：06 月样表零件号改成 `551003095AA` → `ECM_PART_NOT_AS_OF`；不要另发明一套扫变更单的停号码
- [ ] 有切点后 SOP 把 115AA 工艺材料改掉再传 07 → `ECM_PROCESS_MATERIAL_CHANGED`；回滚该号旧刀后再切过
- [ ] 振华已成功 `MAT-202506`，全鑫同项目同月再传一本同版本不因振华那本 `ECM_VERSION_DUPLICATE`
