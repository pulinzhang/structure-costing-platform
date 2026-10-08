# 异步任务 — 设计说明

> 状态：**已上线**  
> 关联：[架构导读 §8–§9](../architecture.md)、[架构宪法 §五](../../.cursor/rules/architecture-constitution.mdc)、[API 类型安全](../../.cursor/rules/api-type-safety.mdc)  
> 现网：`app/services/async_task/`、`app/repositories/async_task/`、`app/models/async_task/task.py`、`app/schemas/dto/async_task_dto.py`、`app/schemas/vo/async_task_vo.py`、`tests/async_task/test_worker_runner.py`

长任务（上传、核算、引擎、LLM 报告）立刻返回 `task_id`，后台用**一份**进程内 runner 执行。进度写辅助库，前端轮询各业务路由上的 `/tasks/{task_id}`。

---

## 0. 范围

本切片只做三件事：建任务、记进度、在后台线程里跑切片提供的 `work`。

| 归属 | 内容 |
|------|------|
| **本切片** | 辅助库行、状态与进度、线程池、任务 Session 的开关、未捕获异常的回滚与终态 |
| **业务切片** | 入队前校验、`work` 里的解析/计算/落库、成功文案、`result` JSON、崩溃时释放计算锁或回写领域行 |
| **业务 Router** | 权限、调 `start_*`、把 `AsyncTaskAcceptedVO` 交给 `ApiResponse.ok`、查进度 |

同步 Excel 与旁路 Session 的封闭名单在架构宪法 §五。本切片不服务那两类。

没有独立的 `/api/async-task`。进度 HTTP 挂在各业务路由上。

---

## 1. 为什么单独成切片

进度若写在主业务库，长事务会挡住轮询。辅助库（`AuxiliaryDatabaseConfig`，`AUXILIARY_DATABASE_URL`）与主库物理隔离；进度写入用独立连接、`AUTOCOMMIT`，一次写完即可被其它进程读到。

Runner 放在已有切片 `app/services/async_task/`，不进 `app/common/`。各长任务复用这一份，不在 Router 或切片里再写一套「开 Session、记进度、catch、close」。

执行器是进程内 `ThreadPoolExecutor`（`max_workers=4`，线程名 `async-task`）。不引入 Celery / Redis。进程退出后，队列里尚未跑完的任务不会续跑；辅助库里的行留到过期清理。

---

## 2. 数据

表 `async_tasks` 在辅助库（`AuxiliaryBase`），只存轮询要用的字段。

| 列 | 含义 |
|----|------|
| `task_id` | UUID 字符串，唯一 |
| `task_type` | 业务类型，轮询时用来对上本路由 |
| `status` | `pending` / `running` / `completed` / `failed` |
| `progress` | 0–100 |
| `message` | 当前阶段说明；失败时可带完整清单 |
| `result_json` | 终态业务结果的 JSON 字符串 |
| `operator_id` / `operator_name` | 提交人 |
| 审计列 | `created_by` / `updated_by` / `created_at` / `updated_at`（`AuditUserMixin`） |

索引：`task_id`、`task_type`、`status`、`updated_at`。

存活时间 `TASK_TTL_SECONDS = 3600`。`create_task` 时按 `updated_at` 删掉更早的行。过期后再轮询得到 404（文案「任务不存在或已过期」）。

---

## 3. 状态与可见性

```
create_task          pending, progress=0
run_in_worker_session 一开始   running, progress=1, start_message
on_progress          running, 切片给定的进度与说明
work 返回            outcome 原样写入（通常 completed 或 failed, progress=100）
未捕获异常            failed；进度默认 0，调用方可传 crash_progress
```

中间进度有节流：距上次写入不足 1 秒、进度变化小于 3、且未到 100，则跳过本次写库。终态（`completed` / `failed`）和带 `result` 的写入不节流。节流状态在进程内存里，只影响写频率；轮询读的是辅助库。

写失败：终态记 `logger.exception`；中间进度记 debug。业务 `work` 仍按原异常路径结束。

读进度用短生命周期 Session，用完即关。写进度不走这条 Session，由 Service 打开 AUTOCOMMIT 连接后交给 Repository。

---

## 4. 调用契约

切片入队固定两步，都在 Service 里完成，请求返回前只做第一步的插入和第二步的提交，不等待 `work` 结束。

```
task = AsyncTaskService().create_task(task_type=..., message=..., operator_id=..., operator_name=...)
AsyncTaskService().submit_session_worker(task.task_id, start_message=..., work=..., on_crash=..., ...)
return AsyncTaskAcceptedVO(task_id=task.task_id)
```

`work` 签名：

```
def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome
```

`db` 由 runner 用主库 `DatabaseConfig.get_session_factory()` 新开。请求级 Session 禁止传入线程。`on_progress(progress, message)` 把阶段写进辅助库。

`WorkerTaskOutcome` 四个字段：`status`、`message`、`result`（可空）、`progress`（默认 100）。`result` 在切片里用 `model_dump(mode="json")` 收成可 JSON 化的对象；runner 只 `json.dumps` 存进 `result_json`。

切片自己接住的业务失败（例如 `BusinessException`）应 `rollback` 后 **返回** `status=failed` 的 outcome。这样半截 flush 不会跟失败任务一起提交。未捕获异常才进 runner：

1. 记异常日志  
2. `db.rollback()`  
3. 若提供了 `on_crash(db, error)`，再调一次（释放计算锁、把报告行标失败等）。回调再失败只记日志  
4. 任务标 `failed`，文案来自 `crash_message`，缺省 `str(error)`；`crash_result` 可附结果 JSON  
5. `finally` 里 `db.close()`

`on_crash` 里的领域提交由切片自己 `commit`。runner 不认识零件数、缺单价、`run_id`。

计算类终态可经 `outcome_from_calc_status`：领域 `result.status == "failed"` 映射为任务 `failed`，其余映射为 `completed`。

引擎 worker 内禁止再 `submit` 子任务并等待。

---

## 5. HTTP

受理：`POST` 返回 **200**，`ApiResponse[AsyncTaskAcceptedVO]`，body 只有 `task_id`。工厂用 `ok`，不用 `created`。

进度：`GET …/tasks/{task_id}`，`ApiResponse[AsyncTaskProgressVO]`。

| VO 字段 | 来源 |
|---------|------|
| `status` | `pending` \| `running` \| `completed` \| `failed` |
| `progress` | 0–100 |
| `msg` | 表字段 `message` |
| `result` | `parse_result_json` 之后，再用本切片结果 VO `model_validate` |
| `operator_id` / `operator_name` | 提交人 |
| `updated_at` | 秒级时间戳 |

`task_id` 是字符串路径参数，与同前缀静态路由放在同一个 `APIRouter`，静态路径写在前面。

两种查进度接法：

| 接法 | 谁组装 VO | 现网 |
|------|-----------|------|
| Router 直读快照 | Router 调 `require_snapshot(task_id, TASK_TYPE_…)`，类型不符或行不存在则 404；再 `parse_result_json` + 本切片结果 VO | 上传、多数核算 |
| 切片 Service | Router 把 `db` 与 `task_id` 交给本切片 `get_task_progress` | 引擎（任务行过期时用 Run 补终态）、LLM 报告（只允许查看本人任务） |

两种接法的进度数字都来自辅助库快照。领域表只补充 `result` 或做权限，不代替进度行。

---

## 6. 任务类型

常量集中在 `app/services/async_task/service.py`。新增长任务时在这里登记一个 `TASK_TYPE_*`，入队与轮询使用同一个值。

| 常量 | 值 |
|------|----|
| `TASK_TYPE_POLICY_UPLOAD` | `steel_price_policy_upload` |
| `TASK_TYPE_BASE_PRICE_IMPORT` | `steel_base_price_import` |
| `TASK_TYPE_STAMPING_UPLOAD` | `stamping_upload` |
| `TASK_TYPE_STAMPING_DIE_UPLOAD` | `stamping_die_upload` |
| `TASK_TYPE_STAMPING_DIE_FEE_CALC` | `stamping_die_fee_calc` |
| `TASK_TYPE_STAMPING_PROCESS_FEE_CALC` | `stamping_process_fee_calc` |
| `TASK_TYPE_STEEL_PRICE_CALC` | `steel_price_calc` |
| `TASK_TYPE_STAMPING_PART_COST_CALC` | `stamping_part_cost_calc` |
| `TASK_TYPE_BOM_UPLOAD` | `bom_upload` |
| `TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE` | `bom_welding_process_breakdown_generate` |
| `TASK_TYPE_BOM_WELDING_FEE_CALC` | `bom_welding_fee_calc` |
| `TASK_TYPE_ASSEMBLY_COST_CALC` | `assembly_cost_calc` |
| `TASK_TYPE_COSTING_ENGINE_RUN` | `costing_engine_run` |
| `TASK_TYPE_ENGINEERING_CHANGE_UPLOAD` | `engineering_change_upload` |
| `TASK_TYPE_ENGINEERING_CHANGE_MATERIAL_UPLOAD` | `engineering_change_material_upload` |

LLM 报告的类型常量写在 `app/services/llm/report.py`：`TASK_TYPE_LLM_ANALYSIS_REPORT = "llm_analysis_report"`。runner 只把它当 `task_type` 字符串。

---

## 7. 前端

各业务页轮询自己的 `/tasks/{task_id}`，间隔约 1.5–2 秒，页面 `destroy` 时清掉定时器。助手里的轮询在 `static/js/llm-assistant/task/poller.js`。平台没有第二套任务中心页面。

---

## 8. 代码地图

| 文件 | 职责 |
|------|------|
| `app/services/async_task/service.py` | `create_task`、`submit_session_worker`、`run_in_worker_session`、快照、节流、过期清理、`parse_result_json` |
| `app/services/async_task/worker_runner.py` | `WorkerTaskOutcome`、`WorkerWork`、崩溃回调类型、`outcome_from_calc_status` |
| `app/repositories/async_task/async_task_repository.py` | 按 `task_id` 读；在 Service 传入的连接上插入、更新、按时间删除 |
| `app/models/async_task/task.py` | `async_tasks` |
| `app/schemas/dto/async_task_dto.py` | `AsyncTaskInsert`、`AsyncTaskPatch` |
| `app/schemas/vo/async_task_vo.py` | `AsyncTaskAcceptedVO`、`AsyncTaskProgressVO` |
| `app/common/types/repository_types.py` | `AsyncTaskSnapshot` |

包 `__init__.py` 不导出。调用方写到模块：`from app.services.async_task.service import AsyncTaskService`。

---

## 9. 硬约束

- 有 `task_id`、前端轮询的工作走本 runner。Router 只调切片 `start_*`（或引擎 `start_run`）。  
- 切片提供 `work(db, on_progress) -> WorkerTaskOutcome`，可选 `on_crash`。Session、进度、统一 catch、`close` 留在 runner。  
- 进度写辅助库 AUTOCOMMIT。Repository 不对请求或任务的业务 Session 调用 `commit`。  
- 任务 `result` 的 `model_dump` 在切片 Service。进度查询用 `parse_result_json` 再 `model_validate`。  
- 类型不符或行已清理：`NotFoundException`（404）。入队前的业务拒绝仍由切片抛 `BusinessException`。
