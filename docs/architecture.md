# 结构件自动核价平台 - 架构说明

> 面向开发者的架构导读。  
> **硬约束以 Cursor Rules / docs 规范为准**（见文末「规范索引」）；本文解释「为什么」与「长什么样」。  
> 领域设计按切片放在 `docs/{slice}/`，目录见 [README.md](README.md)。

---

## 1. 项目概述

| 项目 | 说明 |
|------|------|
| 名称 | 结构件自动核价平台（小名：核价平台） |
| English | Structural Parts Automated Costing Platform（short: Costing Platform） |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | `static/` SPA（无 Webpack/Vite：原生 ES Module + 入库的 `tailwind.css`） |
| 做什么 | 总成 / 分总成 / 冲压件按月自动核价；工艺/政策/BOM/工程变更入库 → 钢材联动与零件、总成核价 → 查询、审核、导出；AI 解读动因 |
| 典型流程 | 上传 Excel → Parser 解析 → Service 落库 → 下游 costing 组合计算 |

---

## 2. 两套正交结构

本项目同时用两套组织方式，不要混为一谈：

| 维度 | 是什么 | 作用 |
|------|--------|------|
| **分层** | Router → Service → Repository → Model | 请求怎么走、谁能碰数据库 / Parser |
| **垂直切片** | `stamping` / `yishiyiyi` / `bom` / `costing` / … | 按业务功能切目录，每层对齐 |

```
请求：  Router ──► Service ──► Repository ──► Database
响应：  Database ──► Repository ──► Service ──► Router（ApiResponse[T]）
```

Parser 是**横向工具**：只被 Service 调用；禁止依赖 Router/Service/Repository，**允许** `app/common/` 纯函数。

---

## 3. 分层职责（摘要）

| 层 | 做什么 | 不要做什么 |
|----|--------|------------|
| **Router** | 鉴权依赖、参数、调 Service、返回 `ApiResponse`；下载/导出可 `StreamingResponse` / `FileResponse` | 业务逻辑、`db.query`、调 Parser、后台 worker 壳、把 Service 错误元组转 `HTTPException` |
| **Service** | 业务规则、事务、调 Parser/Repo、ORM→VO、抛业务异常 | 直接写 SQL；用 `(None, str)` 向 Router 报错；手写 datetime/Decimal JSON |
| **Orchestrator** | 核算指挥：`prepare → engine → persist` | 主方法里 `for` / 掐进度 / 写库（见 [指挥家宪法](orchestrator-constitution.mdc)） |
| **Repository** | CRUD / 聚合查询；返回 Model 或具名 `TypedDict`（函数体 `return {…}` 合法） | 权限/角色分支决策；签名写成匿名 `dict` / `dict[str, Any]` |
| **Model** | 表字段 + `relationship`（同切片附属行） | `to_dict`、业务 `@property`；跨切片独立主数据禁止父指向子（引用保护） |
| **Schema** | DTO（`schemas/dto/`）/ VO（`schemas/vo/`） | 业务流程 |
| **Parser** | 纯解析，无副作用 | 依赖 Router/Service/Repository |

餐厅类比：Router=服务员，Service=厨师，Repository=仓管，Database=冰箱。

硬表见 [架构宪法](../.cursor/rules/architecture-constitution.mdc)。

---

## 4. 垂直切片与依赖方向

### 4.1 切片一览

| 角色 | 切片 | 典型内容 |
|------|------|----------|
| **上游 / 基础数据** | `masterdata` · `settings` · `stamping` · `bom` · `yishiyiyi` | 基地/项目/供应商/牌号分类、用户配置、工艺零件、BOM、基价/政策/废料价 |
| **下游 / 编排核价** | `costing` · `dashboard` | 钢材联动、零件核价、成品核价、引擎编排、KPI |
| **解释层（隔离特例）** | `llm` | 核价结果自然语言分析；只读上游表；内部工具不进 `common`；上游不得依赖它 |
| **横切登记** | `file_trace` | 已落盘 Excel 登记与鉴权下载；被上游上传 Service 调用，**不**依赖 costing |
| **横切基础设施** | `app/common/` | 权限、审计、时区、金额量化等纯函数（**不**依赖业务切片） |

目录按 feature 对齐，例如：

```
app/models/stamping/      app/routers/stamping/     app/services/stamping/     app/repositories/stamping/
app/models/costing/       app/routers/costing/      app/services/costing/      app/repositories/costing/
app/models/file_trace/    app/routers/file_trace.py app/services/file_trace/   app/repositories/file_trace/
app/models/yishiyiyi/     …
app/parsers/stamping/     # 仅上传类切片有 Parser
```

前端 `static/js/features/` 与侧栏菜单树同样按功能对齐（见 [前端规范](front-end.mdc)）。

### 4.2 有向依赖（禁止成环）

核价平台天然要「下游组合上游数据」。规则：

```
✅ costing / dashboard / engineering_change  →  调用 stamping、yishiyiyi、bom、masterdata、settings（Service 或 Repository）
✅ llm → 只读上游结果表 Model（不经上游 Service→VO）；内部工具留在本切片
✅ stamping / bom / yishiyiyi / engineering_change 上传 Service → file_trace.register_existing（横切登记）
❌ stamping / bom / yishiyiyi →  依赖 costing、dashboard、llm、engineering_change（上游不得依赖下游）
❌ file_trace → costing（登记切片不得依赖核价）
❌ 把 llm 内部工具抽到 app/common（污染主业务）
❌ 同层互相 import 成环
```

`engineering_change`（工程变更）是 **完全独立** 的下游切片：自有菜单/API/表/前端；通过调用 `bom` / `stamping` / `masterdata` 等 **Service** 完成跨域写入。**bom/stamping/costing 不得 import 它**；三条整包门禁文案进 `app/common/engineering_change_gates.py`。细则见 [工程变更设计 §4.7](engineering-change/part-number-revision-design.md)。

优先序：上游稳定查询 API → 只读上游 Repository（批量/导出/热路径）→ 真正无归属的算法再进 `common/`。

> 旧版「切片一律禁止互依、只能走 common」已废弃；以架构宪法「切片依赖」为准。

### 4.3 引用保护（谁引用谁负责）

**数据引用**和 **4.2 代码依赖** 方向相反：下游可以 import 上游；父不得 import / 点名子。拦改主键和删除的是数据库引擎，不是父在应用里 `count` 子行。

- 外键只加在设计图**直接下一跳**（子表 `ForeignKey(..., ondelete="RESTRICT", onupdate="RESTRICT")`）
- 父改主键或删除只动自己；仍被引用 → `IntegrityError` → `BusinessException("仍被引用，不能修改")` / `BusinessException("仍被引用，不能删除")`
- 有外键的独立主数据必须**同时提供修改和删除**：非主键修改（启用/禁用）外键不管；改主键与删除都走 `RESTRICT`
- `CASCADE` 只给没有独立身份的附属行（`ondelete` 与 `onupdate` 都 `CASCADE`）；独立主数据之间改主键和删除都用 `RESTRICT`
- **例外：** 钢材联动价结果行上「当初用了哪条基价/政策」的可选 ID 允许 `SET NULL`（档案可重导，账留下）。这是外键策略，与有没有 `task_id` 无关。列名单只在 [架构宪法](../.cursor/rules/architecture-constitution.mdc) §3.3，禁止扩到身份主键

细则见 [架构宪法](../.cursor/rules/architecture-constitution.mdc)「引用保护」。

---

## 5. 目录结构（现状）

```
stamping-costing-platform/
├── main.py                      # FastAPI 入口
├── app/
│   ├── config.py / database.py
│   ├── common/                  # 横切：permissions / audit / timezone / money …
│   ├── models/{feature}/        # ORM（按垂直切片）；根 __init__ 仅供 main 注册表
│   ├── schemas/                 # dto/ + vo/；任意层级 __init__.py 只作标记
│   ├── repositories/{feature}/  # 任意层级 __init__.py 只作标记
│   ├── services/{feature}/      # 路径形状以 BOM 为准；任意层级 __init__.py 只作标记
│   ├── routers/{feature}.py     # 单职责叶子；仅拆职责才成包（crud/calc/upload/export）
│   ├── parsers/{feature}/       # 有文件解析的切片；任意层级 __init__.py 只作标记
│   └── utils/                   # 日志、ApiResponse 等
├── static/                      # 前端 SPA
│   ├── index.html / login.html
│   ├── css/style.css
│   └── js/
│       ├── main.js / app.js / permissions.js / page-size.js
│       └── features/…           # 与菜单对齐的页面模块
├── docs/                        # 规范与说明（含本文件）
├── .cursor/rules/               # Agent 规范正文（按 glob / alwaysApply 加载）
├── data/                        # SQLite
├── uploads/                     # 上传与简图
└── logs/
```

---

## 6. API 契约要点

- 统一包装：`ApiResponse[T]`（`code` / `success` / `message` / `data`）
- 分页：列表查询参数必须是 `page` + `size`（禁止 HTTP `skip` / `limit`）；`data` 内为 `PageResult`（`items` / `total` / `page` / `page_size` / …）；`list_(items=..., page=..., page_size=...)`
- 长任务 `start_*` 入队：HTTP 200 + `ApiResponse.ok(data=accepted)`，不要套 POST 201。同步 Excel 的 `POST …/upload` 不入队，直接返回结果 VO（入口只在宪法 §五）
- 下载/导出：`StreamingResponse` / `FileResponse`，不走 `ApiResponse`
- 业务路由：`Depends(require_perm(Perm.…))`；写操作把 `current_user` 显式传给 Service
- Service 返回 VO；Repository 返回 Model（聚合签名用具名 `TypedDict`，函数体 `return {…}` 合法；禁止签名写成匿名 `dict`）
- **禁止** Model.`to_dict`；JSON 形态用 VO `@field_serializer`（金额/物理量字符串；datetime **必须** `app.common.timezone.datetime_to_iso`）

细则：[架构宪法](../.cursor/rules/architecture-constitution.mdc)（归属）+ [类型安全](../.cursor/rules/api-type-safety.mdc)（形态）。

### Router 示例（示意）

```python
from app.services.stamping.part.service import StampingPartService

@router.get("/parts", response_model=ApiResponse[PageResult[PartVO]])
def list_parts(
    db: Session = Depends(get_db),
    query: StampingPartQuery = Depends(),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
) -> ApiResponse[PageResult[PartVO]]:
    records, total = StampingPartService().paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
    )
```

---

## 7. 前端架构（摘要）

| 项 | 说明 |
|----|------|
| 入口 | 主应用 `index.html`；登录独立 `login.html` → `/login` |
| 路由 | Hash：`#/stamping-parts`；内容挂 `#pageContent` |
| 页面协议 | `pageConfig = { render, init, destroy? }` + `pageMeta` |
| 全局 | `main.js`（非 module）暴露 `HttpClient` / `esc` / `showToast` … |
| 列表表 | 默认对齐 HUD 密表（零件价格一览为参照）；允许例外 |

完整约定：[前端规范](../.cursor/rules/front-end.mdc)。

---

## 8. 数据流示例：上传工艺 Excel（长任务）

下图只描述**工艺这类长任务**：立刻返回 `task_id`，后台 runner 开新 Session。名册/窄表类是**同步 Excel**（请求内解析、无 `task_id`），不要拿本图当所有 `upload` 的模板。三种形态见 §9；同步入口只在宪法 §五。

```
浏览器 POST /api/stamping/…upload
        │
        ▼
Router（权限 + 文件校验）──► Upload Service.start_upload
        │                         │
        │                         ├── create_task + submit（立即返回 task_id）
        │                         └── 后台：async_task runner 开独立 Session
        │                                    └── 指挥家 execute（预备 → 管线 → 落库）
        ▼
ApiResponse[AsyncTaskAcceptedVO]
前端轮询 GET …/tasks/{task_id}
```

核价计算则是下游 Service **组合**上游零件、政策、基价、废料价等，再写入 costing 表；长计算同样走 `start_calc` + runner，不要在 Router 里开 Session。

硬约束见 [架构宪法](../.cursor/rules/architecture-constitution.mdc) §五。

---

## 9. 长任务、同步 Excel、旁路 Session

三种形态（硬名单与禁止事项只在 [架构宪法](../.cursor/rules/architecture-constitution.mdc) §五，本文不抄入口表）：

| 形态 | 请求怎么结束 | 谁开 Session |
|------|----------------|--------------|
| **长任务** | 立刻 200 + `task_id`，前端轮询 | `async_task` runner（禁止切片自开） |
| **同步 Excel** | 本次请求内解析完，返回条数等结果 VO | 请求级 `db`（仅宪法 §五那张入口表） |
| **旁路 Session** | 与主请求无关，无进度 UI | 调用方自开（仅宪法 §五那张场景表） |

请求级 `db` 不能带进线程。Router **两种上传都只调 Service**：长任务 `start_*`；同步 Excel 本切片 `upload`。禁止在 Router 里解析文件或写 worker 壳。

| 谁 | 做什么 |
|----|--------|
| **Router** | 校验；调 `start_*` 或同步 `upload`；返回 `AsyncTaskAcceptedVO` 或结果 VO；查进度 |
| **切片 Service** | 长任务：`start_*` 入队（`create_task` + `submit_session_worker`）；worker 调指挥家 `execute`（或核算 `calculate`）；成功文案；任务终态；崩溃时释放计算锁或回写引擎 Run |
| **`async_task` runner** | 仅服务长任务：任务 Session、`on_progress` 写辅助库、统一 catch、关 Session |

公共 runner 放 `app/services/async_task/`（已有切片归属），**不要**进 `common/`，也**不要**为每个长任务复制一份 60 行 worker。

**不要做：** 在 Router 写 `_process_*_in_background`；长任务（上传 / 核算 / 引擎 / LLM 报告）自开 `get_session_factory()`；让 runner 知道「零件数 / 缺单价 / `run_id`」；为此换 Celery；引擎 worker 内再 `submit` 子任务死等。引擎 `start_run`、LLM 报告的 Session / 进度必须走公共 runner。

---

## 10. 添加功能的推荐顺序

1. **Schema**：DTO / VO  
2. **Model**（若新表）+ 迁移/建表策略按项目惯例  
3. **Repository**  
4. **Service**（含权限相关业务判断、事务、业务异常；新上传先对照宪法 §五：默认长任务 `start_*` + runner；只有名单内入口才同步 `upload`）  
5. **Router**（JSON：`response_model` + `require_perm` + `ApiResponse`；下载例外；不要翻译业务错误）  
6. **前端**：`pageMeta` + `app.js` 注册 + 侧栏 `data-page` + 权限码  
7. 递增前端脚本 `?v=`

跨切片读取时确认依赖方向（§4.2），不要引入上游→下游环。

---

## 11. 常见问题

### Service 和 Repository 区别？

- Service：做什么（规则、组合、事务、Parser）  
- Repository：怎么查/写库（无角色 if）

教学硬约束：**Repository 禁止 `db.commit` / `db.rollback`**，只 `flush`；写成功后由 Service `commit`，失败 `rollback`。口诀：Repo 只改会话，Service 才落库。  
特例：异步进度由 runner 经辅助库 AUTOCOMMIT 写入；计算锁 DDL 用独立连接；操作日志等旁路 Session 见架构宪法 §五（不进请求/任务业务事务）。

### 简单查询也要 Service 吗？

要。保持 Router 永不直连 Repository，便于统一权限与响应形态。

### 业务失败该返回元组还是抛异常？

抛异常。Service 对 Router：不存在 → `NotFoundException`（404）；普通拒绝 → `BusinessException`（400）；期别冲突 → `BusinessException(..., code=409)`。全局 handler 按 `exc.code` 转 `ApiResponse.fail`。禁止 `(None, str)`，禁止 Router 入口返回 `VO | None` / `bool` 再判空。**业务 Router / 切片 Service 不抛 `HTTPException`**（未登录只在 `deps/auth`）。分页 `(items, total)`、Parser 匹配结果不是错误通道。未预期错误 rollback 后原样抛（500），不要包成 `BusinessException(str(e))`。细则见 [架构宪法](../.cursor/rules/architecture-constitution.mdc)「事务与异常通道」。不要用 `ValidationException`；请求体校验走 Pydantic。

### `start_*` 该用 201 还是 200？

200。立刻返回 `task_id` 用 `ApiResponse.ok(data=accepted)`。`created()` / 201 只给 CRUD 创建。同步 Excel 的 `upload` 也是 200 + 结果 VO，不是 201，也不是 `task_id`。

### 下载接口要套 ApiResponse 吗？

不要。Excel / 原件用 `StreamingResponse` 或 `FileResponse`。

### 跨切片该不该抽到 common？

领域数据留在所属切片；下游直接组合上游即可。只有**无自然归属**且多方复用的横切能力才进 `common/`。**`llm` 内部工具（金额展示、年月键等）留在本切片，禁止抽到 `common/`**，以免摊进核价主路径。细则见 [LLM 设计 B.2.1](llm/llm-costing-analysis-report-design.md)。

### Model 可以有 relationship 吗？

同切片附属行可以（零件→工序、主单→明细）。禁止的是业务方法与 `to_dict`。跨切片、独立主数据之间禁止父指向子的 `relationship`，引用由子表外键承担（架构宪法「引用保护」）。

### 删除或改主键时该不该先查有没有人用？

不该在父切片里查。直接下游在自己的 Model 上声明 `ON UPDATE RESTRICT` + `ON DELETE RESTRICT`，由数据库拒绝；父只把 `IntegrityError` 译成「仍被引用，不能修改」或「仍被引用，不能删除」。修改与删除必须同时提供。核价结果表上的可选溯源 ID 见宪法 §3.3 `SET NULL` 名单（基价/政策可重导；与 Session / `task_id` 无关）。细则见 [架构宪法](../.cursor/rules/architecture-constitution.mdc)「引用保护」。

### 后台解析/计算为什么不能写在 Router？为什么有的 upload 又没有 `task_id`？

两件事不要混：

- **长任务**（工艺、政策、核算、引擎、LLM）：请求 `db` 在响应后关闭，线程必须新开 Session；进度、失败标任务、关 Session 是横切壳，应只有一份 runner。Router 只调 `start_*`。成功文案和释放计算锁仍在切片 Service。引擎 / LLM 即使在 Service 里 `submit`，也不得自建 Session/进度壳。
- **同步 Excel**（仅宪法 §五那张入口表）：没有后台线程，Router 调本切片 `upload`，仍禁止在 Router 里解析或写库。不是漏做异步。不要把工艺/政策/核算/引擎/LLM 改成这种。

---

## 12. 规范索引

领域设计按切片放在 `docs/{slice}/`，完整目录见 [docs/README.md](README.md)。

### 平台（本目录根）

| 文档 | 位置 | 用途 |
|------|------|------|
| **架构宪法** | [`.cursor/rules/architecture-constitution.mdc`](../.cursor/rules/architecture-constitution.mdc) | 分层、切片依赖、外键、事务、异常通道、长任务 / 同步 Excel / 旁路 Session |
| **指挥家宪法** | [`.cursor/rules/orchestrator-constitution.mdc`](../.cursor/rules/orchestrator-constitution.mdc) | Orchestrator 主方法只编排 |
| **前端规范** | [`.cursor/rules/front-end.mdc`](../.cursor/rules/front-end.mdc) | SPA / Brabus / HUD；改 `static/` 时按 glob 加载 |
| **浅色主题** | [light-theme-design.md](light-theme-design.md) | 浅色主题改造（设计） |
| **命名规范** | [`.cursor/rules/naming-convention.mdc`](../.cursor/rules/naming-convention.mdc) | 标识符命名（always-apply） |
| **API 类型安全** | [`.cursor/rules/api-type-safety.mdc`](../.cursor/rules/api-type-safety.mdc) | `ApiResponse` / Decimal / `Perm.*` / `Any` 边界 |
| **Python 执行** | [`.cursor/rules/python-execution.mdc`](../.cursor/rules/python-execution.mdc) | Windows / UTF-8（always-apply） |
| **权限设计** | [permission-design.md](permission-design.md) | 前后端权限码 |
| **FastAPI 指南** | [fastapi-guide.md](fastapi-guide.md) | 框架约定 |
| **生产安装** | [deploy-windows-production.md](deploy-windows-production.md) | Windows 一键安装 |

`docs/` 下同名 `.mdc` / `api-type-safety.md` 只做索引，**不要**再复制规则全文。

### 领域（`docs/{slice}/`）

| 切片 | 文档 |
|------|------|
| **masterdata** | [基地](masterdata/location-design.md)（已落地）· [项目](masterdata/vehicle-model-design.md)（本切片已落地；下游改读另做）· [供应商](masterdata/supplier-design.md)（第一期 + 第二期已落地：采购对象可空指定、工艺/采购对象 `RESTRICT`、一览改主键/删除）· [牌号分类](masterdata/steel-grade-category-design.md)（已落地：手工档案，下游只读） |
| **stamping** | [产品质量先期策划（APQP）先布点后工艺](stamping/stamping-apqp-die-before-process-design.md) · [工艺确认表](stamping/stamping-process-confirmation-design.md) · [模具布点](stamping/stamping-die-management-design.md) · [模具单价](stamping/stamping-die-unit-price-design.md) · [检具费档案](stamping/stamping-gauge-fee-design.md) · [年度模具费（不含检具）](stamping/stamping-die-fee-design.md) |
| **bom** | [年度零件价](bom/bom-annual-part-prices-design.md) · [焊接工艺拆解](bom/welding-process-breakdown-design.md) · [焊接费](bom/welding-fee-design.md) · [采购对象清单](bom/bom-procurement-objects-design.md) · [指定供应商](bom/bom-procurement-object-supplier-design.md) · [批量上传供应商](bom/bom-procurement-object-supplier-upload-design.md) |
| **engineering-change** | [目录](engineering-change/README.md) · [有效期（已落地）](engineering-change/bom-process-die-effective-period-design.md) · [工程变更切片+权限+契约（设计）](engineering-change/part-number-revision-design.md) · [T28 对照/拆测](engineering-change/t28-2025-07-import-bundle-test-design.md) |
| **yishiyiyi** | [分类级厚度政策](yishiyiyi/thickness-policy-category-level-design.md) |
| **costing** | [核价引擎](costing/costing-engine-design.md) · [总成核价](costing/assembly-costing-design.md) · [L0 成品核价（冻结）](costing/l0-assembly-costing-design.md) · [采购价格协议](costing/procurement-contract-report-design.md) · [协议价生效期](costing/effective-period-design.md) · [暂估正式](costing/provisional-final-settlement-design.md) · [锚点送货](costing/anchor-true-up-design.md) |
| **file_trace** | [文件溯源](file-trace/file-trace-design.md) |
| **llm** | [切片实现导读](llm/llm-slice-design.md) · [产品契约](llm/llm-costing-analysis-report-design.md) |

规范正文只改 `.cursor/rules/`；改完不必再贴一份到 `docs/`。
