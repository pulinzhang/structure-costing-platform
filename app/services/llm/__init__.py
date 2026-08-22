"""
LLM 垂直切片 — Service 层包根。

子包职责（新增能力只进对应子包，禁止在包根平铺新模块）：

| 子包 | 职责 | 禁止 |
|------|------|------|
| `catalog/` | Schema 字段真相（C9） | 查业务库、调 LLM |
| `context/` | Context Pack：只调上游 Service（C12） | 直连 Repository / SQL |
| `analysis/` | 报告生命周期：幂等、AsyncTask、生成 | 核价重算、另建取数 |
| `prompts/` | Prompt 静态资源 + PromptRegistry | 业务取数、改金额 |
| `client/` | 模型 HTTP 客户端 | 读核价表、组 Pack |
| `export/` | 报告导出（P2，待实现） | 生成业务金额 |
"""
