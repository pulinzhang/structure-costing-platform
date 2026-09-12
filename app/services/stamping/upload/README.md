# 冲压工艺上传（`upload/`）

解析 Excel、落盘、写零件/工序。主数据单一大事务；进度写辅助库。

对外入口：`StampingUploadService`（`stamping_upload.py`）。

## 架构

门面入队；`orchestrate` 校验范围并提交事务；`persist` 写文件与库。

## 职责

| 模块 | 职责 |
|------|------|
| `stamping_upload.py` | 异步入队、对外入口 |
| `orchestrate.py` | 解析后校验范围、进度、提交事务 |
| `persist.py` | 文件/简图落盘、零件工序写库、牌号归一 |
| `cost_ratio_preserver.py` | 已设成本系数回写 |
| `template_builder.py` | 导入模板 |
