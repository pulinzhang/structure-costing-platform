"""
Schema 字段真相（C9）。

已落地：
- `field_labels.py` — 受控中文覆盖表（键名必须与 VO 属性一致）
- `schema_catalog.py` — 从现网 VO 投影 schema_card / allowlist / Pack 预设

不查业务库；不算价；不调模型。
"""

from app.services.llm.catalog.schema_catalog import (
    SchemaCard,
    SchemaFieldCard,
    build_merged_pack_schema_card,
    build_pack_schema_card,
    build_schema_card,
    format_schema_card_markdown,
    project_mapping,
    schema_card_fingerprint,
)

__all__ = [
    "SchemaCard",
    "SchemaFieldCard",
    "build_schema_card",
    "build_pack_schema_card",
    "build_merged_pack_schema_card",
    "format_schema_card_markdown",
    "project_mapping",
    "schema_card_fingerprint",
]
