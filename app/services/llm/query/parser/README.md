# Query 规则拆分（`parser/`）

问句 → `AnalysisQuery` 的规则层。对外仍：

```python
from app.services.llm.query.query_parser import QueryParser
```

`QueryParser.parse` 只编排：抽条件 → 词典对齐 → 上一问沿用 → 钉月或沿用时间 → 定 analyses/subject。  
**不是**核算 Orchestrator；口语表再长也不要塞进指挥家。

改 `carry.py` 前先跑 `tests/llm/test_query_carry.py`。顺序不能倒：先证据覆盖再钉月；抽取失败不得清空已补槽。

| 文件 | 改什么时候打开 |
|------|----------------|
| `pipeline.py` | 降级链条、就绪/帮助旁路、组装 filters |
| `carry.py` | 上一问范围沿用（证据覆盖、缺槽补、从属槽作废） |
| `subjects.py` | 新实体列表问句 → `subject`（**顺序即优先级**） |
| `analyses.py` | `analyses[]` 组合 |
| `part_price.py` | 问价口语、单件下钻 vs 总览 |
| `draft.py` | LLM 失败时的 time/filters 草稿 |
| `pin_latest.py` | 无明确时间时钉核价表最新月 |
