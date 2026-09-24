# 冲压工艺上传编排（`part/upload/orchestrator/`）

指挥家主方法只做预备 → 管线 → 落库。

对外入口：`StampingUploadOrchestrator`（`orchestrator.py`）。包 `__init__.py` 不汇总导出。

## 文件

| 模块 | 职责 |
|------|------|
| `orchestrator.py` | 指挥：`prepare` → `pipeline` → `persist` |
| `prep.py` | 解析并做门禁。不插零件、不 commit |
| `pipeline.py` | 落盘与 flush 写库。不 commit |
| `persist.py` | commit，组装导入结果。不再插零件 |
| `types.py` | 预备包、管线包、进度回调 |
