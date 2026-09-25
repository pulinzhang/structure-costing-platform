# 逻辑引用 — 设计说明

> 状态：**已落地**  
> 归属：`settings` 下独立目录 `logical_ref`。表 `logical_ref`、`logical_ref_filter`。  
> 与外键检查分开。外键见 `docs/settings/schema-comment-design.md`。两边目录互不引用。  
> 引用保护的总规则见架构宪法 §3.3。

---

## 0. 一句话

> **删一行时，若计算结果表不能用外键挡住，就按配置写明结果表是什么、表名、过滤条件，生成器拼出计数。有结果就不删。**

---

## 1. 为什么不走外键

外键只表达「子表某一列等于父行某一列」。钢材联动价没有指向零件或材料变更的外键。它按基地、牌号、料厚，以及账期是否落在生效窗口里对上。账期是 **≥** 生效，不是相等。只写成 `year = effective_year` 会漏掉更晚的月份。

这类检查不向库发现外键，不读 `schema_comment`、`ref_hint`。已有外键不删、不改。删除前两次调用：先 `ensure_deletable`，再 `ensure_logical_deletable`。

| 层 | 做什么 | 手段 |
|----|--------|------|
| 结果表 | 挡住的是哪张计算结果表、它是什么 | `logical_ref.result_table`、`result_name` |
| 过滤 | 结果表上比哪一列、怎么比、值从哪来 | `logical_ref_filter` 每一行 |
| 计数 | 这些过滤同时成立的有几条 | 生成器把过滤 AND 成 `COUNT` |
| 删除 | 有结果则停 | 异常正文就是原因，见 `app/services/settings/logical_ref/delete.md`。调用方不执行 `DELETE` |

---

## 2. 规则

| # | 规则 |
|---|------|
| L1 | 调用方交出当前 `Session`、正在删的表名、按列名给的键值，以及可选主语。不在调用处写结果表名或过滤列 |
| L2 | 一张结果表一份种子。启动只补还没有的头和过滤，不改已有行，不删种子里没有的配置。表由启动建表建立 |
| L3 | 放行、挡住、操作员看到的正文，只写在 `app/services/settings/logical_ref/delete.md` |
| L4 | 生成器不按表名分支。新的结果表只加头和过滤，并在该条删除前单独调用 |
| L5 | 标识符只允许普通表名、列名，值用绑定参数。不 `commit`，不开新连接 |

---

## 3. 表

### 3.1 `logical_ref`

一行是：删某张表时，要检查的一张结果表。

| 列 | 含义 |
|----|------|
| `deleted_table` | 正在删除的表。主键之一 |
| `result_table` | 结果表表名，如 `steel_prices`。主键之一 |
| `result_name` | 结果表是什么，如钢材联动价 |
| `hint` | 处理建议，写成侧栏路径「请到「…」处理」 |

### 3.2 `logical_ref_filter`

一行是一条过滤。同一对 `deleted_table`、`result_table` 上按 `seq` 用 AND 拼进结果表的 `WHERE`。

| 列 | 何时填写 | 含义 |
|----|----------|------|
| `compare` | 必填 | 见 §4 |
| `result_column` | `eq` | 结果表上等值的列，如 `grade` |
| `result_year_column` / `result_month_column` | 账期 | 结果表账期，如 `year` / `month` |
| `value_table` | 值不在被删行上 | 取值表。空表示正在删的这一行 |
| `value_column` / `value_month_column` | 必填来源 | 等值时的取值列；账期时再填月列 |
| `join_from_column` / `join_to_column` | 填了 `value_table` | 被删行哪一列连到取值表哪一列 |
| `next_table`、`next_mode`、`next_group_*`、`next_year_column`、`next_month_column` | `period_before_next` | 下一行在哪张表、怎么取 |
| `skip_when` | 可选 | 被删行这些列任一为 1，则本条过滤不算。逗号分隔 |

---

## 4. 过滤算子

| `compare` | 成立条件 |
|-----------|----------|
| `eq` | 结果表列 = 取值列 |
| `period_gte` | 结果账期 ≥ 取值账期。年更大，或同年且月 ≥ |
| `period_lte` | 结果账期 ≤ 取值账期。取值年为空则不封顶 |
| `period_before_next` | 结果账期早于下一行。没有下一行则本条不挡。一月的前一月是上一年十二月，用「年小于，或同年且月小于」表达，不单独减月 |

`next_mode`：

| 值 | 下一行 |
|----|--------|
| `first` | 分组内最早一行 |
| `after` | 严格晚于本行生效的最早一行。本行生效写在该过滤的 `value_column` / `value_month_column` |

---

## 5. 查询怎么拼

对每一张结果表：

```text
SELECT COUNT(*) FROM 结果表 AS hit
WHERE EXISTS (
  SELECT 1 FROM 正在删的表 AS src
  [JOIN 取值表 …]
  WHERE src.键 = :被删行
    AND 过滤1 AND 过滤2 AND …
)
```

同一对表上的 `value_table` 加连接列相同，只 JOIN 一次。

---

## 6. 样例：钢材联动价

结果表表名 `steel_prices`，是钢材联动价。钢材联动没有零件号。同一基地、同一牌号、同一料厚有结果就会挡住，不限零件。料厚按数值比较，`1.5` 与 `1.5000` 算同一条。

这次只登记这两份。拼焊子片不登记：子片随零件级联删除，子片材料产生的钢材联动挡不住。零件价、加工费、模具费、总成核价不登记。

过滤列以种子为准，文档不另抄一份。

- 删 `stamping_parts`：`app/services/settings/logical_ref/seeds/stamping_parts.py`
- 删 `stamping_part_material_changes`：`app/services/settings/logical_ref/seeds/material_change.py`。料厚用零件的 `thickness`，不用 `after_thickness`。材料变更自己没有失效列。止月是下一刀生效的前一月，并且还要落在零件生失效之内。

---

## 7. 代码放哪

与用户、系统参数、操作日志，以及外键目录 `foreign_key/` 分开。

| 角色 | 位置 |
|------|------|
| 表 | `app/models/settings/logical_ref/model.py` |
| 生成查询 | `app/repositories/settings/logical_ref/sql.py` |
| 读写 | `app/repositories/settings/logical_ref/repository.py` |
| 检查 | `app/services/settings/logical_ref/service.py` 的 `ensure_logical_deletable` |
| 写入入口 | `app/services/settings/logical_ref/seed.py` |
| 零件工艺材料种子 | `app/services/settings/logical_ref/seeds/stamping_parts.py` |
| 材料变更种子 | `app/services/settings/logical_ref/seeds/material_change.py` |
| 启动 | `app/bootstrap/lifecycle.py` 在外键种子之后调用 |

删除调用点：冲压零件删除、材料变更删除（含材料变更回滚里删历史行）、设计变更回滚里删新建零件。调用处只传正在删的表和键，不写 `steel_prices` 的列。
