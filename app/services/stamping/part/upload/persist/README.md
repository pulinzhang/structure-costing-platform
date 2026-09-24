# 冲压工艺上传落库（`part/upload/persist/`）

落盘与 flush。不 commit。commit 在 `orchestrator/persist.py`。

禁止本包 `__init__.py` 再导出。

## 文件

| 模块 | 职责 |
|------|------|
| `files.py` | Excel 与零件简图落盘 |
| `parts.py` | 零件与工序 flush。不 commit |
