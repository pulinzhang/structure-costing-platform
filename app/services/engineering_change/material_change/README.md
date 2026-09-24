# 材料变更 Service（`engineering_change/material_change/`）

同号只切材料。本包只存这一本 Excel。历史的写入和删除调 `StampingMaterialChangeService`。读工艺身份调 `StampingDesignChangeService`。

| 你要做什么 | 打开 |
|---|---|
| 列表 / 回滚 | [list/README.md](list/README.md) |
| 下载模板 / 入队上传 | [upload/README.md](upload/README.md) |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/engineering-change/material`。设计见 [docs/engineering-change/material-change/](../../../../docs/engineering-change/material-change/README.md)。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `list/` | 查询与回滚 |
| `upload/` | 模板、门禁、编排 |
