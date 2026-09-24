# 拼焊子片（`part/tailor_weld/`）

材料侧挂在父件上。工序仍在父件。有子片时父件 `is_tailor_welded=True`，清空后改回 `False`。

对外入口：`StampingTailorWeldBlankService`（`service.py`）。

禁止本包 `__init__.py` 再导出。
