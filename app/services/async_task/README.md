# 异步任务 Service（`async_task/`）

设计说明：[docs/async-task/async-task-design.md](../../../docs/async-task/async-task-design.md)。

入队、进度快照、worker 执行。各切片 upload/calc 经本包发任务，不自己起线程。

| 你要做什么 | 调 |
|---|---|
| 创建 / 查进度 / 解析结果 JSON | `service.AsyncTaskService` |
| worker 循环 | `worker_runner` |

任务进度 HTTP 挂在各业务路由的 `/tasks/{task_id}`，没有独立 `/api/async-task`。禁止本包 `__init__.py` 再导出。

## 目录

| 文件 | 职责 |
|------|------|
| `service.py` | 状态机与快照 |
| `worker_runner.py` | 进程内 worker |
