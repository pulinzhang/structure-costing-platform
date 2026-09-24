# 材料变更路由（`/api/engineering-change/material`）

`__init__.py` 不转发 `router`。权限码和页面键见 [服务包 README](../../../services/engineering_change/material_change/README.md)。

| 方法 | 路径 | 做什么 |
|---|---|---|
| GET | `/template` | 下载空模板 |
| POST | `/upload` | 入队 |
| GET | `/upload/tasks/{task_id}` | 进度 |
| GET | `/uploads` | 列表 |
| GET | `/uploads/{upload_log_id}/file` | 原件 |
| DELETE | `/uploads/{upload_log_id}` | 整本回滚 |
| GET | `/parts/{part_id}/records` | 零件抽屉切点 |
