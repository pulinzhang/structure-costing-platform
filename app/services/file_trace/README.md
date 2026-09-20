# 文件溯源 Service（`file_trace/`）

上传文件落盘路径、类别、哈希登记。各切片导入成功后调用，不在业务表里存绝对路径。

| 你要做什么 | 调 |
|---|---|
| 列表 / 下载元数据 | `upload_file_service.UploadFileService` |
| 导入后登记 | `register.register_existing` |
| 允许的文件类别 | `categories` |
| 相对路径换算 | `path_utils` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/file-trace`。

## 目录

| 文件 | 职责 |
|------|------|
| `upload_file_service.py` | 查询门面 |
| `register.py` | 写入登记 |
| `categories.py` | 类别白名单 |
| `path_utils.py` | 路径规范化 |
