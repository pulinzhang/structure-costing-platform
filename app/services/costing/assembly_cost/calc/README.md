# 成品月核价 calc（`assembly_cost/calc/`）

纯函数 rollup + 编排。无本目录 IO；取价与落库在 orchestrator。

`rollup_assembly` 从 `rollup.py` 导出。

## 职责

| 模块 | 职责 |
|------|------|
| `rollup.py` | 材料 walk、成卡金额汇总（材料 + 焊接 + 间接） |
| `rollup_models.py` | 数据结构、间接费代码、公式版本 |
| `identities.py` | 金额恒等式、quantize |
| `indirects.py` | 间接费行、费率文案 |
| `tree.py` | 叶子取价、子孙遍历、路径数量 |
| `orchestrator/` | 就绪检查、prep、逐卡落库 |
| `process_log.py` | 过程文案 / 核价卡 JSON |
