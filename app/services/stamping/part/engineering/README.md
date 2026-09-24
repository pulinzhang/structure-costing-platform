# 冲压零件工程变更（`part/engineering/`）

设计变更和材料变更分开。下游各自调用，不经一个总门面。

禁止本包 `__init__.py` 再导出。

## 目录

| 目录 / 文件 | 职责 |
|------|------|
| `design_change/` | 设计变更工艺零件：当月命中、改图 clone、写入、回滚 |
| `material_change.py` | `StampingMaterialChangeService`：插入、删除、列出、详情、当月叠材料。不改工艺行 `material` |
