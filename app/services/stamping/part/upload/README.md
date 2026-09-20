# 冲压工艺上传（`part/upload/`）

入口在本包根：`upload_service`（门面）、`start_upload`（入队）、`template_builder`（下载模板）。
编排类：`orchestrator.orchestrator.StampingUploadOrchestrator`。校验帮手在 `gates/`；flush 适配在 `persist/`。

对外入口：`StampingUploadService`（`upload_service.py`）。Router 只依赖本类。

## 架构

| 层 | 职责 |
|------|------|
| `upload_service.py` | 模板 + 入队转发 |
| `start_upload.py` | 校验文件后 `create_task` + worker 调指挥家 |
| `orchestrator/` | 预备 → 管线 → 落库（主方法三行） |
| `gates/` | 能不能写；不写库 |
| `persist/` | 落盘与 flush；不 commit |
| `cost_ratio_preserver.py` | 已设成本系数回写 |
| `materials.py` | 牌号改写（预备调用；不是门禁） |
| `template_builder.py` | 导入模板 |
