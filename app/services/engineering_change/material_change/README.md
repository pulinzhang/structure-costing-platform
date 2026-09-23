# 材料变更（占位）

同号只切 `material`。这次只有目录，没有业务。设计按刀落地，见 [docs/engineering-change/material-change/](../../../../docs/engineering-change/material-change/README.md)。

落地时写入 catalog：

- 分组 `menu:engineering-change-material-group`，与设计变更并列，挂一级「工程变更」
- `menu:engineering-change-material-upload` / `menu:engineering-change-material-list`
- 任务类型 `engineering_change_material_upload`
- 接口前缀：`/api/engineering-change/material`

路由包 `__init__.py` 不要转发 `router`。
