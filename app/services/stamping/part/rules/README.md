# 冲压零件规则（`part/rules/`）

纯校验，不写库。工艺确认表上传与模具布点共用。

禁止本包 `__init__.py` 再导出。

## 文件

| 模块 | 职责 |
|------|------|
| `part_seq_validator.py` | 零件序号从 1 连续编号 |
| `process_seq_validator.py` | 同一零件下工序号不得重复 |
