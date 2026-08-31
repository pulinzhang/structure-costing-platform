# 核价导出归档与内部溯源 — 设计说明

> 状态：**结论为暂不落地**（下文仅作方案留底）  
> 用途：若有人拿着一份 Excel 争「当时就是这个数」，用整文件 SHA256 对归档原件。  
> 关联：`docs/permission-design.md`

---

## 要不要做

**本期不要实现。**

内部扯皮对的是 **库里的已审核价行**（谁算的、谁审的、单件成本是多少），不是邮件里的 xlsx。现网列表、审核状态、操作日志已经能回答「系统当时是什么价」。再做导出落盘 + hash + 验真页，只解决「这份附件有没有被改过」——那是附件层面的事，不是核价真相。

| 实际在争什么 | 现网够不够 | 要不要本文 |
|--------------|------------|------------|
| 这个零件本期单价到底多少 | 已审结果表 | 不要 |
| 谁导出过、导出条件是什么 | 不关键；需要可看操作日志 | 不要 |
|  circulated 的 Excel 被改格子后又拿回来争 | 少见；真发生了用库里的数否掉附件即可 | 不要先做 |

只有出现固定痛点再开工：同一范围的表在内部传来传去，且经常拿附件当证据、不认系统。那时再按下文做。在那之前，维护已审数据与审核链比做 hash 更值。

---

## 0. 一句话

> **关键导出原样落盘，记下 SHA256 和操作人、时间、范围。** 以后谁拿来一份表说「系统当时就是这个数」，登录后对一下指纹就能结。

日常自己看数，继续用「导出 Excel」（可不落盘）。要对得上责任、版本时，用「导出并归档」。

---

## 1. 通用能力

与具体业务表无关，任何核价导出都可以挂：

| 能力 | 说明 |
|------|------|
| 原样归档 | 与当时导出同一份字节，不改表头、不改格子、不印指纹 |
| 台账 | 谁、何时、哪一类导出、什么范围、行数、指纹短显、下载原件 |
| 内部验真 | 须登录。上传文件，和台账 hash 比：原件 / 已改 / 对不上 |
| 内部报告 | 打印范围、归档人、时间戳、hash、比对结果，给内部了结争议 |

Hash 算法公共一份：`app/common/excel_integrity.py`。台账一张表，用 `archive_kind` 区分业务。验真接口按指纹查全表，不依赖「对方知不知道文档号」。

不做：无登录校验、表上印 hash/二维码、外部门户、电子签章、单元格 diff、写入文件溯源（溯源只登记上传原件）。

---

## 2. 第一期落地：冲压零件价格

复用 `export_process_sheet`，不改表体。

| 项 | 规则 |
|----|------|
| `archive_kind` | `stamping_part_cost` |
| 范围 | 年、月、基地、冲压工厂必须齐全 |
| 数据 | 仅已审；该范围有计算失败则整单拒绝 |
| 权限 | 沿用 `op:stamping-part-cost:export` |
| 次数 | 同一范围可多次归档；旧档保留（扯皮常对着当时那一封附件） |

流程：

```
范围 + 仅已审
    → 现网导出函数
    → 字节落盘
    → file_hash = SHA256(整文件)
    → 插入 export_archives
    → 下载同一份字节
```

其它导出（合册、钢材等）以后只加 `archive_kind` 和各自范围校验，不另做一套 hash。

---

## 3. Hash 与验真

| 函数 | 作用 |
|------|------|
| `sha256_bytes` / `sha256_file` | 整文件指纹 |
| `short_hash` | 台账短显 |

权威在库里的 `file_hash`。Excel 里不写文档号、不写自定义属性。上传只算 hash，不保存。

| 判定 | 条件 |
|------|------|
| 原件 | 等于某条归档的 `file_hash` |
| 已改 | 对不上（格子改过、另存结构变了，指纹都会变） |
| 对不上 | 不是本系统归档件 |

---

## 4. 内部报告

从台账生成，仅登录用户下载。

- 标题：导出归档验真（内部）  
- 业务类型、范围、归档时间、操作人、行数  
- `document_id`、`file_hash`  
- 若上传比对：判定  

一期打印页即可。

---

## 5. 分层与表

```
app/common/excel_integrity.py
app/models/costing/export_archive.py
app/repositories/costing/export_archive_repository.py
app/services/costing/export_archive_service.py          # 通用：落盘、验真、报告
app/services/costing/stamping_part_cost/…               # 第一期：组范围、调现网导出、调通用归档
app/routers/costing/stamping_part_cost/crud.py          # 第一期 HTTP
```

落盘（禁止无鉴权静态直链）：

```
export-archives/{archive_kind}/{year}/{month}/{location}/{scope_key}/{document_id}.xlsx
```

`scope_key` 第一期用冲压工厂名；其它 kind 自行约定。

### 5.1 表 `export_archives`

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `document_id` | UUID，内部用 |
| `archive_kind` | 如 `stamping_part_cost` |
| `year` / `month` / `location` / `stamping_supplier` | 范围；某 kind 用不到的可空 |
| `row_count` | |
| `file_hash` | SHA256，索引 |
| `stored_relpath` | UNIQUE |
| `file_size` | |
| `original_filename` | |
| `status` | `active` / `revoked` |
| AuditUserMixin | 归档人 |

索引：`(archive_kind, year, month, location, stamping_supplier, created_at DESC)`、`file_hash`、`document_id`。

---

## 6. 第一期 API

前缀 `/api/costing/stamping-part-cost`，全部登录。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `POST` | `/export-archives` | `EXPORT` | 归档后前端 download |
| `GET` | `/export-archives` | `VIEW` | 台账 |
| `GET` | `/export-archives/{document_id}/download` | `EXPORT` | 原件 |
| `POST` | `/export-archives/{document_id}/revoke` | `EXPORT` | 误档作废 |
| `POST` | `/export-archives/verify` | `VIEW` 或 `EXPORT` | 上传比对 |
| `GET` | `/export-archives/{document_id}/report` | `EXPORT` | 内部报告 |

Service 收 `current_user=`。缺范围 / 有失败行 / 含待审 → `BusinessException`；无记录 → `NotFoundException`。

验真也可按 `file_hash` 命中其它 `archive_kind` 的档（同一张表）。第一期 UI 只挂在零件价格一览。

---

## 7. 第一期前端

`stamping-part-cost/list`：

- 保留「导出 Excel」  
- 「导出并归档」：范围不全则禁用；toast「已归档」  
- 台账抽屉：短指纹、下载、作废、报告、上传验真  
- `can('op:stamping-part-cost:export')`  

---

## 8. 实施与测试

| 步 | 可验收 |
|----|--------|
| `excel_integrity` | 固定字节 → 固定 hex |
| 表 + 落盘 | 有 xlsx |
| 归档 + 下载 | 范围齐全才能档；下载 hash 与库一致 |
| 验真 | 原件 / 改一格 / 无关文件 |
| 台账 / 作废 / 报告 | 可打印 |

不改 `process_sheet` 表体。合册不自动归档。

- 归档件与同筛选内部导出字节一致  
- 两次归档（数据已变）→ 两个 `document_id`、两套 hash  
- 未登录不能验真、不能下载  
- 缺范围 / 失败行 / 待审 → 不能归档  

---

## 9. 开放点

1. 归档是否单独权限码。  
2. 报告是否以后改 PDF。  
3. 下一类导出何时挂上（钢材、合册等）。

---

## 10. 决策摘要

| 项 | 结论 |
|----|------|
| 目的 | 内部留证，防扯皮 |
| 做法 | 导出原样落盘 + SHA256 |
| 验真 | 仅登录 |
| 第一期 | 冲压零件价格已审导出 |
| 扩展 | 同表 `archive_kind` |
| 文件溯源 | 不登记 |
