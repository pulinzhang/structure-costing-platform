# 汽车冲压件自动核价平台 - 架构说明

> 面向开发者的架构导读。  
> **硬约束以 Cursor Rules / docs 规范为准**（见文末「规范索引」）；本文解释「为什么」与「长什么样」。

---

## 1. 项目概述

| 项目 | 说明 |
|------|------|
| 名称 | 汽车冲压件自动核价平台 |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | `static/` SPA（无构建：原生 ES Module + Tailwind CDN） |
| 做什么 | 工艺/政策/BOM 等数据入库 → 钢材联动与零件核价 → 查询、审核、导出 |
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

Parser 是**横向工具**：只被 Service 调用，不依赖其它层。

---

## 3. 分层职责（摘要）

| 层 | 做什么 | 不要做什么 |
|----|--------|------------|
| **Router** | 鉴权依赖、参数、调 Service、返回 `ApiResponse` | 业务逻辑、`db.query`、调 Parser、后台 worker 壳（§5.3） |
| **Service** | 业务规则、事务、调 Parser/Repo、ORM→VO | 直接写 SQL |
| **Repository** | CRUD / 聚合查询；返回 Model 或聚合结果 | 权限/角色分支决策 |
| **Model** | 表字段 + `relationship` | `to_dict`、业务 `@property` |
| **Schema** | DTO（入）/ VO（出） | 业务流程 |
| **Parser** | 纯解析，无副作用 | 依赖 Router/Service/Repository |

餐厅类比：Router=服务员，Service=厨师，Repository=仓管，Database=冰箱。

详细正反例见 [架构宪法](architecture-constitution.mdc)。

---

## 4. 垂直切片与依赖方向

### 4.1 切片一览

| 角色 | 切片 | 典型内容 |
|------|------|----------|
| **上游 / 基础数据** | `settings` · `stamping` · `bom` · `yishiyiyi` | 用户配置、工艺零件、BOM、基价/政策/废料价 |
| **下游 / 编排核价** | `costing` · `dashboard` | 钢材联动、零件核价、成品核价、引擎编排、KPI |
| **横切登记** | `file_trace` | 已落盘 Excel 登记与鉴权下载；被上游上传 Service 调用，**不**依赖 costing |
| **横切基础设施** | `app/common/` | 权限、审计、时区等（**不**依赖业务切片） |

目录按 feature 对齐，例如：

```
app/models/stamping/      app/routers/stamping/     app/services/stamping/     app/repositories/stamping/
app/models/costing/       app/routers/costing/      app/services/costing/      app/repositories/costing/
app/models/file_trace/    app/routers/file_trace/   app/services/file_trace/   app/repositories/file_trace/
app/models/yishiyiyi/     …
app/parsers/stamping/     # 仅上传类切片有 Parser
```

前端 `static/js/features/` 与侧栏菜单树同样按功能对齐（见 [前端规范](front-end.mdc)）。

### 4.2 有向依赖（禁止成环）

核价平台天然要「下游组合上游数据」。规则：

```
✅ costing / dashboard  →  调用 stamping、yishiyiyi、bom、settings（Service 或只读 Repository）
✅ stamping / bom / yishiyiyi 上传 Service → file_trace.register_existing（横切登记）
❌ stamping / yishiyiyi →  依赖 costing、dashboard（上游不得依赖下游）
❌ file_trace → costing（登记切片不得依赖核价）
❌ 同层互相 import 成环
```

优先序：上游稳定查询 API → 只读上游 Repository（批量/导出/热路径）→ 真正无归属的算法再进 `common/`。

> 旧版「切片一律禁止互依、只能走 common」已废弃；以宪法 §四 为准。

---

## 5. 目录结构（现状）

```
stamping-costing-platform/
├── main.py                      # FastAPI 入口
├── app/
│   ├── config.py / database.py
│   ├── common/                  # 横切：permissions / audit / timezone …
│   ├── models/{feature}/        # ORM（按垂直切片）；根 __init__ 仅供 main 注册表
│   ├── schemas/                 # dto/ + vo/
│   ├── repositories/{feature}/
│   ├── services/{feature}/
│   ├── routers/{feature}/
│   ├── parsers/{feature}/       # 有文件解析的切片
│   └── utils/                   # 日志、ApiResponse 等
├── static/                      # 前端 SPA
│   ├── index.html / login.html
│   ├── css/style.css
│   └── js/
│       ├── main.js / app.js / permissions.js / page-size.js
│       └── features/…           # 与菜单对齐的页面模块
├── docs/                        # 规范与说明（含本文件）
├── .cursor/rules/               # Cursor 始终应用的规则副本
├── data/                        # SQLite
├── uploads/                     # 上传与简图
└── logs/
```

---

## 6. API 契约要点

- 统一包装：`ApiResponse[T]`（`code` / `success` / `message` / `data`）
- 分页：`data` 内为 `PageResult`（`items` / `total` / `page` / …），不要把 `total` 摊在根上
- 业务路由：`Depends(require_perm(Perm.…))`；写操作把 `current_user` 显式传给 Service
- Service 返回 VO；Repository 返回 Model（聚合接口可返回 dict / 轻量结构）
- **禁止** Model.`to_dict`；序列化用 VO + `@field_serializer`

细则：[架构宪法](architecture-constitution.mdc) + 项目内 `api-type-safety` 规则。

### Router 示例（示意）

```python
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

完整约定：[前端规范](front-end.mdc)（与 `.cursor/rules/front-end.mdc` 同步）。

---

## 8. 数据流示例：上传工艺 Excel

```
浏览器 POST /api/stamping/…upload
        │
        ▼
Router（权限 + 文件校验）──► Upload Service.start_upload
        │                         │
        │                         ├── create_task + submit（立即返回 task_id）
        │                         └── 后台：async_task runner 开独立 Session
        │                                    └── process_upload → Parser → Repository
        ▼
ApiResponse[AsyncTaskAcceptedVO]
前端轮询 GET …/tasks/{task_id}
```

核价计算则是下游 Service **组合**上游零件、政策、基价、废料价等，再写入 costing 表；长计算同样走 `start_calc` + runner，不要在 Router 里开 Session。

硬约束见宪法 [§5.3](architecture-constitution.mdc)。

---

## 9. 异步后台任务（目标态）

上传 / 计算立即返回 `task_id`，后台线程跑业务。请求级 `db` 不能带进线程。

| 谁 | 做什么 |
|----|--------|
| **Router** | 校验、调 `service.start_*`、返回 `AsyncTaskAcceptedVO`、进度查询 |
| **切片 Service** | `create_task` + `submit`；真正的 `process_upload` / `calculate` / 引擎 `execute`；成功文案；任务终态；崩溃时释放计算锁或回写引擎 Run |
| **`async_task` runner** | 独立业务 Session、`on_progress` 写辅助库、统一 catch、关 Session |

公共 runner 放 `app/services/async_task/`（已有切片归属），**不要**进 `common/`，也**不要**为每个切片复制一份 60 行 worker。

**不要做：** 在 Router 写 `_process_*_in_background`；把同一套壳复制进多个 Service（**含引擎 worker**）；让 runner 知道「零件数 / 缺单价 / `run_id`」；为此换 Celery；引擎 worker 内再 `submit` 子任务死等。

**落地范围（已落地）：**
- 9 个上传/计算 Router 的 `_process_*_in_background` 已删除，改为 `service.start_*`
- **核价引擎** `CostingEngineService`：`start_run` 仍在 Service 提交；Session / 进度 / `db.close()` 走 `submit_session_worker`；`RunDeletedError`、回写 Run 失败态留在引擎 Service
- LLM 报告 worker **不在本批**（已在 Service 内 submit，可随后靠拢）

---

## 10. 添加功能的推荐顺序

1. **Schema**：DTO / VO  
2. **Model**（若新表）+ 迁移/建表策略按项目惯例  
3. **Repository**  
4. **Service**（含权限相关业务判断、事务；异步上传/计算/引擎用 `start_*` + `async_task` runner，见 §9）  
5. **Router**（`response_model` + `require_perm`）  
6. **前端**：`pageMeta` + `app.js` 注册 + 侧栏 `data-page` + 权限码  
7. 递增前端脚本 `?v=`

跨切片读取时确认依赖方向（§4.2），不要引入上游→下游环。

---

## 11. 常见问题

### Service 和 Repository 区别？

- Service：做什么（规则、组合、事务、Parser）  
- Repository：怎么查/写库（无角色 if）

教学硬约束：**Repository 禁止 `db.commit` / `db.rollback`**，只 `flush`；写成功后由 Service `commit`，失败 `rollback`。口诀：Repo 只改会话，Service 才落库。  
特例（仍由 Service 提交）：异步任务进度由 `async_task` runner 经辅助库 AUTOCOMMIT 写入（宪法 §5.3）；计算锁 DDL 用独立连接，`conn.commit()` 在 Service。

### 简单查询也要 Service 吗？

要。保持 Router 永不直连 Repository，便于统一权限与响应形态。

### 跨切片该不该抽到 common？

领域数据留在所属切片；下游直接组合上游即可。只有**无自然归属**且多方复用的横切能力才进 `common/`。

### Model 可以有 relationship 吗？

可以。禁止的是业务方法与 `to_dict`。

### 后台解析/计算为什么不能写在 Router？

请求 `db` 在响应后关闭，线程必须新开 Session；进度写辅助库、失败标任务、关 Session 是横切壳，应只有一份 runner。Router 只调 `start_*`。成功文案和释放计算锁仍在切片 Service。引擎虽然已在 Service 里 `submit`，同样不得自建 Session/进度壳。

---

## 12. 规范索引

| 文档 | 位置 | 用途 |
|------|------|------|
| **架构宪法** | [architecture-constitution.mdc](architecture-constitution.mdc) · `.cursor/rules/architecture-constitution.mdc` | 分层 + 切片依赖硬规则 |
| **前端规范** | [front-end.mdc](front-end.mdc) · `.cursor/rules/front-end.mdc` | SPA / Brabus / 表格风格 |
| **命名规范** | [naming-convention.mdc](naming-convention.mdc) · `.cursor/rules/…` | 标识符命名 |
| **API 类型安全** | [api-type-safety.md](api-type-safety.md) · `.cursor/rules/api-type-safety.mdc` | `ApiResponse` / `PageResult` / 权限 Depends / `Any` 不进函数签名 |
| **Python 执行** | `.cursor/rules/python-execution.mdc` | Windows/UTF-8 跑脚本约定 |
| **权限设计** | [permission-design.md](permission-design.md) | 前后端权限码 |
| **L0 成品核价设计** | [l0-assembly-costing-design.md](l0-assembly-costing-design.md) | 供货总成月度总账、外购/L1 年度价（已上线：计算/一览/导出） |
| **BOM 年度零件价表** | [bom-annual-part-prices-design.md](bom-annual-part-prices-design.md) | 外购价 / L1 一口价单表（已上线：上传/列表/审核） |
| **核价引擎设计** | [costing-engine-design.md](costing-engine-design.md) | 基地+年+月一键编排（已上线） |
| **文件溯源设计** | [file-trace-design.md](file-trace-design.md) | 已落盘 Excel 登记与鉴权下载（MVP 已上线；深链/导出等见文内非目标） |

`docs/*.mdc` 与 `.cursor/rules/*.mdc` 应对齐；改规范时两处一起改。
