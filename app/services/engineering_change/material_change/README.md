# 材料变更（占位）

同号只切牌号。这次只有目录，没有业务、菜单、权限码、溯源分类。

以后落地时再用、这次不写进 catalog 的名字：

- 分组文案「材料变更」，与「设计变更」并列，挂在一级「工程变更」下（不新开一级、不摊平四个叶子）
- 权限码 `menu:engineering-change-material-upload`、`menu:engineering-change-material-list` 及对应 `op:`，不复用设计变更的上传/删除码
- 溯源分类键 `engineering_change_material`，展示名「材料变更」
- 页面键 `engineering-change-material-upload`、`engineering-change-material-list`
- 接口前缀已挂上：`/api/engineering-change/material`（[router.py](../../../routers/engineering_change/material_change/router.py) 零个接口）

有 Model 之后，要从 [app/models/engineering_change/__init__.py](../../../models/engineering_change/__init__.py) 和 [app/models/__init__.py](../../../models/__init__.py) 导出，建表扫描才看得到。路由包 `__init__.py` 不要转发 `router`。
