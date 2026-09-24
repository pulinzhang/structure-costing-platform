# 设计变更工艺零件（`part/engineering/design_change/`）

改图按一个零件做完再做下一个：clone 出零件一行、每一道工序、每一条材料变更历史，再按这个顺序写入。增加零件没有旧号，不 clone 历史。

对外入口：`StampingDesignChangeService`（`service.py`）。包 `__init__.py` 不汇总导出。

## 文件

| 模块 | 职责 |
|------|------|
| `service.py` | 入口：当月命中、clone、写入、回滚。按一个零件依次调用下面的写入 |
| `as_of.py` | 当月命中零件；工艺材料字是否在档案 |
| `clone.py` | clone 零件、全部工序、全部材料变更历史。不写库 |
| `insert.py` | 写入 clone 出的三样。有旧号时停旧零件并 clone 拼焊子片。只 flush |
| `rollback.py` | 删新零件及其工序，清空旧零件失效月。材料变更历史由调用方先删 |
| `types.py` | 写入规格、clone 出的历史、当月命中行 |
