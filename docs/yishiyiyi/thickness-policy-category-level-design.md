# 厚度加减价政策 — 分类级引入改造说明

> 状态：**设计定稿（待开发）**  
> 关联：`docs/masterdata/steel-grade-category-design.md`、`app/models/yishiyiyi/steel_price_policy.py`、`app/services/costing/steel_price/calc/steps/adjustments/thickness.py`  
> 原则：**只做厚度加减价**（冷轧 / 镀锌 / 酸洗 **三大类均做**）；政策按 **牌号分类大类级** 存储（`grade_type = CATEGORY`，`grade_value` 与块标签共用）；**开发环境清空历史政策后重来**，不做旧数据迁移与兼容。**宽度加减价、厚宽组合、锌层等本期不做。**

---

## 0. 一句话

> **清空 `steel_price_policies` 历史数据后，冷轧 / 镀锌 / 酸洗三个厚度块各按大类落一条 `THICKNESS` 政策（`grade_value` 与块标签共用）；核价经牌号分类档案解析大类后命中对应阶梯。不再导入、不再匹配宽度政策。**

---

## 1. 为什么要改

### 1.1 旧做法（按牌号，即将废弃）

厚度块解析曾按 **每行牌号一条** 政策落库；匹配时 `grade_exact` 按牌号命中。同时系统还维护 **宽度加减价** 等政策块。

开发阶段积累的数据 **不按生产迁移**，直接 **整表清空** 后按新规则重导即可。

### 1.2 本期要解决的问题

| 问题 | 说明 |
|------|------|
| 厚度按牌号膨胀 | 同一大类阶梯在库里复制 N 份，与「大类共用」业务不符 |
| 与牌号分类重叠 | `steel_grade_categories` 已管「牌号 → 大类」；厚度政策不应再按牌号拆行 |
| 范围过大 | **宽度** 本期不用，应从设计与实现路径上 **下线** |

### 1.3 本期业务边界（定死）

| 能力 | 本期 |
|------|------|
| **冷轧 · 厚度加减价** | ✅ 做（大类一条） |
| **镀锌 · 厚度加减价** | ✅ 做（大类一条） |
| **酸洗 · 厚度加减价** | ✅ 做（大类一条） |
| **宽度加减价（`WIDTH`）** | ❌ 不用（导入跳过；核价 **不再调用** `WidthAdjustmentMatcher`） |
| **厚宽组合 / 锌层 / 子组** | ❌ 不做 |
| **历史政策数据** | ❌ **全删**，不迁移、不 `grade_exact` 回退 |

牌号分类档案（`steel_grade_categories`）与政策 **三分类对齐**：档案 `冷轧` / `镀锌` / `酸洗` 的牌号，分别命中对应大类的厚度政策。

---

## 2. 改造目标

| # | 目标 |
|---|------|
| G1 | 开发环境 **清空** `steel_price_policies` + `steel_price_ladder_items`（及关联 file_trace 政策记录，若有） |
| G2 | 厚度政策粒度：**大类一条**（`grade_type = CATEGORY`），不是牌号 |
| G3 | 每个厚度块 → **一条** `THICKNESS` 头表 + 一套阶梯；键含 `category_name`（冷轧钢 / 镀锌钢 / 酸洗钢）与 `base_thickness` |
| G4 | `grade_value` 与块大类标签 **共用**（如 `冷轧钢`、`镀锌钢`、`酸洗钢`） |
| G5 | 阶梯 `items` **结构不变**；区间、金额语义不变 |
| G6 | 核价：经档案解析大类 → 命中 **对应大类** 厚度政策；档案没有该牌号 **硬停** |
| G7 | **移除** 宽度政策导入与核价应用路径 |
| G8 | **无** 旧 per-grade 厚度、旧 WIDTH 数据的兼容与回退 |

---

## 3. 范围边界

### 3.1 做

- 开发库 **清表** + 按新规则 **重导** 含冷轧 / 镀锌 / 酸洗厚度块的政策 Excel  
- Parser：三大类厚度块各 → 大类一条；**跳过** 宽度块、厚宽块  
- Matcher：`CATEGORY` 厚度匹配 + `steel_grade_categories` 解析大类  
- 核价链路：**去掉** 宽度加减价步骤  
- 列表 / 导出：展示 **冷轧 / 镀锌 / 酸洗** 的 `THICKNESS` 政策  
- 引擎硬停：已分类牌号需有 **对应大类** 厚度政策

### 3.2 不做

| 不做 | 说明 |
|------|------|
| 宽度加减价 | 不导入、不匹配、不保留历史 WIDTH 行 |
| 厚宽组合 / 锌层 / 非标长文案块 | 不解析 |
| 历史数据迁移 / 合并脚本 | 开发环境直接删 |
| `grade_exact` 厚度回退 | 新 Matcher **只认** `grade_type=CATEGORY` |
| 改 `steel_price_ladder_items` 表结构 | 阶梯字段不变 |
| 改 `steel_grade_categories` 表结构 | 档案仍三分类 |
| 改基准价表结构 | 基价行仍带 `grade`；核价匹配只认档案大类，不对基价牌号 |

---

## 4. 定稿约定

### 4.1 政策头 — 仅 `THICKNESS` + 三大类块

| 字段 | 取值 | 说明 |
|------|------|------|
| `year`, `month` | 业务期 | 如 `2026`, `1` |
| `steel_mill` | 钢厂 | 如 `唐钢` |
| `category_name` | 块标签 | **`冷轧钢` / `镀锌钢` / `酸洗钢`**（与 Excel 块一致） |
| `policy_type` | `THICKNESS` | 唯一政策类型 |
| `grade_type` | **`CATEGORY`** | 固定 |
| `grade_value` | **与 `category_name` 共用** | 经 `category_aliases` 与档案 `冷轧` / `镀锌` / `酸洗` 互认 |
| `base_thickness` | 如 `1.00` | 不变 |

**业务唯一键**（表约束不变）示例：

```text
(2026, 1, 唐钢, 冷轧钢, THICKNESS, 冷轧钢, 1.00)
(2026, 1, 唐钢, 镀锌钢, THICKNESS, 镀锌钢, 1.00)
(2026, 1, 唐钢, 酸洗钢, THICKNESS, 酸洗钢, 1.00)
```

### 4.2 阶梯明细 — 完全不变

每个厚度区间列一条 `item`：`thick_min/max`、运算符、`price_adjustment`、`is_base`、`sort_order` 与现网一致。  
**「各阶梯依然不变」** — 只改头表条数，不改阶梯模型。

### 4.3 `grade_value` 共用

| 档案 `category_name` | 政策块标签 / `grade_value` | 共用牌号 |
|----------------------|----------------------------|----------|
| `冷轧` | `冷轧钢` | 档案为冷轧的全部牌号 |
| `镀锌` | `镀锌钢` | 档案为镀锌的全部牌号 |
| `酸洗` | `酸洗钢` | 档案为酸洗的全部牌号 |

**匹配链**：`material` → 档案 `grade` → 大类（冷轧/镀锌/酸洗）→ 政策 `grade_type=CATEGORY` + `grade_value` 经 `category_aliases` 命中对应块。

### 4.4 宽度政策 — 本期下线

| 项 | 定稿 |
|----|------|
| 导入 | Parser **不再产出** `policy_type=WIDTH` / `THICKNESS_WIDTH` |
| 存储 | 清表后库中 **无** WIDTH 行 |
| 核价 | `AdjustmentApplier` **不再调用** `WidthAdjustmentMatcher`；**不加宽度调差** |
| 前端 | 政策上传说明 / 列表筛选项去掉「宽度」展示（可选） |

---

## 5. 示例

### 5.1 存储示例

**唐钢 · 2026-01 · 厚度加减价 · base_thickness=1.00**

| year | month | steel_mill | category_name | policy_type | grade_type | grade_value | base_thickness |
|------|-------|------------|---------------|-------------|------------|-------------|----------------|
| 2026 | 1 | 唐钢 | 冷轧钢 | THICKNESS | CATEGORY | 冷轧钢 | 1.00 |
| 2026 | 1 | 唐钢 | 镀锌钢 | THICKNESS | CATEGORY | 镀锌钢 | 1.00 |
| 2026 | 1 | 唐钢 | 酸洗钢 | THICKNESS | CATEGORY | 酸洗钢 | 1.00 |

每个大类 **独立一套** `items`（阶梯区间、金额可不同）。

### 5.2 核价命中（冷轧）

`material = DC03`，档案 `冷轧`，基价钢厂 `唐钢`，`base_thickness = 1.00`：

1. `map_grades("DC03")` → `冷轧`  
2. 命中 `THICKNESS` + `CATEGORY` + `冷轧钢` 政策  
3. 按 `thickness` 落阶梯 → 加减价  

`DC01`、`DC04` 等同属冷轧，**共用冷轧那条政策**。

### 5.3 核价命中（镀锌）

`material = DC51D+Z`，档案 `镀锌`，同期同厂：

1. `map_grades` → `镀锌`  
2. 命中 `镀锌钢` 厚度政策（**不是**冷轧那条）  
3. 按镀锌块阶梯计价  

### 5.4 核价命中（酸洗）

`material = SPHC`，档案 `酸洗` → 命中 `酸洗钢` 厚度政策；逻辑同 §5.2 / §5.3。

### 5.5 导入对比

| 内容 | 旧开发数据（将删除） | 新规则 |
|------|----------------------|--------|
| 冷轧厚度块 10 行牌号 | 10 条 THICKNESS(GRADE) | **1** 条 THICKNESS(CATEGORY, 冷轧钢) |
| 镀锌厚度块 8 行牌号 | 8 条 THICKNESS(GRADE) | **1** 条 THICKNESS(CATEGORY, 镀锌钢) |
| 酸洗厚度块 | 若干条 GRADE | **1** 条 THICKNESS(CATEGORY, 酸洗钢) |
| 宽度块 | 若干条 WIDTH | **0**（跳过） |

---

## 6. 历史数据清理（开发环境）

### 6.1 原则

**不迁移、不合并、不回退。** 开发库 **一次性清空** 政策相关表后重导。

### 6.2 清表范围

| 对象 | 动作 |
|------|------|
| `steel_price_ladder_items` | 全删（或 CASCADE 随主表） |
| `steel_price_policies` | 全删 |
| `file_trace` 中 `steel_price_policy` 类记录 | 建议一并清 |
| `steel_grade_categories` | **保留** |
| `steel_base_prices` | **保留** |

### 6.3 清表后

按新规则导入含 **冷轧 + 镀锌 + 酸洗** 厚度块的政策 Excel，再跑钢材联动试算。

**期货生效月（入库 `year` / `month`）**：文件名括号内为冲焊件原料实际生效年月（订 1 月 → 括号里 2 月）。解析函数：`app/common/policy_effective_period.py`；批量测试脚本：`scripts/import_policy_thickness_samples.py`（目录 `excel_sample/25年-26年一事一议价格/2026年1月-12月一事一议价格`，匹配含「厚度加减价」的 xlsx）。

### 6.4 不提供

- ❌ per-grade → CATEGORY 合并脚本  
- ❌ Matcher `grade_exact` 回退  
- ❌ 宽度历史行保留  

---

## 7. 导入改造（Parser）

### 7.1 三大类厚度块（统一规则）

1. 块定位逻辑可复用现网 `locate_thickness_block`  
2. **`category_name` 归一后属于冷轧系 / 镀锌系 / 酸洗系** 才解析（`冷轧钢`·`冷轧`·`冷扎` / `镀锌钢`·`镀锌` / `酸洗钢`·`酸洗`）；锌层、卷板等非标长文案块 **跳过**  
3. 每块 **一条** `ParsedPolicy`：
   - `grade_type = CATEGORY`
   - `grade_value = block["category_name"]`（如 `冷轧钢`）
   - `items` 取代表行（§7.2）  
4. **禁止** 按牌号行膨胀头表  

### 7.2 代表行与校验

| 排版 | 策略 |
|------|------|
| 合并单元格，价格只在首行 | 取第一个有效数据行的 `items` |
| 每行牌号各有数字 | 取首行；同块其余行与首行 `items` 不一致 → **拒绝导入**（`BusinessException`） |

### 7.3 显式跳过（不入库）

| 块类型 | 处理 |
|--------|------|
| 全部 **宽度** 块 | 不调用宽度解析 |
| `THICKNESS_WIDTH` / 锌层 / 卷板等非三大类标签 | 不解析 |

### 7.4 实现参照（形态 only）

借用「**每块一条政策 + CATEGORY**」装配方式（历史上鞍钢宽度块曾用此形态）；**宽度业务本期废弃**。

### 7.5 政策导入与档案

- **不** 往牌号分类插档；缺档由主数据页手工补  
- 政策只消费档案三分类；基价 / 工艺导入缺牌号则整批拒绝  

---

## 8. 匹配改造（核价 / 预览）

### 8.1 厚度（冷轧 / 镀锌 / 酸洗）

```text
1. row.grade 非空
2. map_grades → category_name（冷轧 / 镀锌 / 酸洗）
3. 档案没有该牌号 → 硬停：「牌号未在分类档案中」
4. 候选：policy_type=THICKNESS 且 grade_type=CATEGORY
5. grade_category(policy, row)：档案大类与 policy.grade_value 经 category_aliases 对齐
6. 钢厂 id 相等，再按 base_thickness 优先（order_by_base_thickness）
7. item_matches_dims（不变）
```

**只认 `CATEGORY`**，**不认** 历史 `GRADE` per-grade 行。

### 8.2 宽度 — 下线

```text
AdjustmentApplier.apply_width → 删除或空实现
CalcRow.width_adjustment → 0
```

### 8.3 缺政策 — 硬停

| 情况 | 处理 |
|------|------|
| 牌号已分类为冷轧，但无 `冷轧钢` 厚度政策 | **硬停** |
| 牌号已分类为镀锌，但无 `镀锌钢` 厚度政策 | **硬停** |
| 牌号已分类为酸洗，但无 `酸洗钢` 厚度政策 | **硬停** |

三类 **对称**，不单独放宽某一类。

### 8.4 波及模块

| 模块 | 改动要点 |
|------|----------|
| `policy_assembler` / handlers | 三大类厚度块各「一块一条」；跳过宽度 |
| `import_service` | upsert 仅 `THICKNESS + CATEGORY` |
| `adjustments/thickness.py` | CATEGORY + 档案大类 |
| `adjustments/width.py` | 停用 |
| `apply_adjustments.py` | 去掉 width 步骤 |
| `winning_thickness` | 厚度路径同 §8.1 |
| `costing-engine` 硬停 | 已分类牌号须有 **对应大类** 厚度政策 |

---

## 9. 上线步骤（开发）

| 步骤 | 动作 |
|------|------|
| 1 | 备份（可选）后 **清空** §6.2 政策表 |
| 2 | 部署 Parser + Matcher（无旧数据兼容分支） |
| 3 | 导入含 **冷轧 + 镀锌 + 酸洗** 厚度的政策 Excel |
| 4 | 确认库中仅有 `THICKNESS + CATEGORY`，且三大类块均有数据 |
| 5 | 钢材联动：三类牌号各命中对应政策；无宽度调差 |
| 6 | 引擎试跑 |

---

## 10. 验收标准

| # | 场景 | 期望 |
|---|------|------|
| A1 | 导入唐钢 2026-01 冷轧厚度块（多行牌号） | **1** 条 THICKNESS(CATEGORY, 冷轧钢) |
| A2 | 同文件含镀锌、酸洗厚度块 | 各 **1** 条 CATEGORY 政策 |
| A3 | 同文件含宽度块 | **0** 条 WIDTH |
| A4 | 三大类阶梯与 Excel 各块首行一致 | items 正确 |
| A5 | 核价：冷轧 DC01 / DC03 同期同厂 | 同一冷轧厚度调差 |
| A6 | 核价：镀锌 DC51D+Z | 命中 **镀锌钢** 政策，不与冷轧串 |
| A7 | 核价：酸洗 SPHC | 命中 **酸洗钢** 政策 |
| A8 | 核价：任意牌号 | **无** 宽度调差 |
| A9 | 已分类牌号缺对应大类政策 | 硬停 |
| A10 | 档案没有该牌号 | 硬停 |
| A11 | 库中无 `grade_type=GRADE` 的 THICKNESS 行 | 清表 + 新导入后成立 |

---

## 11. 已定事项

| # | 事项 | 定稿 |
|---|------|------|
| Q1 | 同块多行阶梯不一致 | **拒绝导入** |
| Q2 | `grade_value` 存法 | 存块标签（`冷轧钢` / `镀锌钢` / `酸洗钢`），匹配走 `category_aliases` |
| Q3 | 历史数据 | **开发环境全删**，不迁移 |
| Q4 | 厚度三大类 | **冷轧 + 镀锌 + 酸洗均做** |
| Q5 | 宽度 | **本期不做** |
| Q6 | 非标块（锌层/卷板长文案） | **不解析** |

---

## 12. 文档与权限

- 落地后更新 `app/services/yishiyiyi/policy/README.md`（厚度三大类 + 宽度下线）  
- `docs/costing/costing-engine-design.md`：硬停改为「已分类牌号须有对应大类厚度政策」；宽度调差移除  
- `docs/masterdata/steel-grade-category-design.md`：已链本文  
- 权限码可不变  

---

## 13. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-08-27 | 初稿：厚度大类级存储；`grade_value` 共用 |
| 2026-08-27 | 收窄：宽度不做；开发环境清历史、不迁移 |
| 2026-08-27 | 定稿：冷轧 / 镀锌 / 酸洗 **三类厚度均做**；仅宽度下线 |
| 2026-08-27 | 落地：清表脚本、大类 CATEGORY 导入/匹配、样例批量导入与期货生效月解析 |
