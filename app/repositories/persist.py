"""Repository 落库辅助：用 DTO / dataclass 写 ORM，禁止 dict[str, Any]。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from sqlalchemy.orm import Query, class_mapper

T = TypeVar("T")

_SKIP_ON_CREATE = frozenset({"id"})


def _mapped_column_names(model: type[object]) -> frozenset[str]:
    mapper = class_mapper(model)
    return frozenset(prop.key for prop in mapper.column_attrs)


def model_from_payload(model: type[T], payload: object) -> T:
    """按 payload 上与 Model 同名的字段构造一行（不写主键）。"""
    instance = model()
    apply_payload_fields(instance, payload, skip=_SKIP_ON_CREATE)
    return instance


def apply_payload_fields(
    instance: object,
    payload: object,
    *,
    skip: frozenset[str] = frozenset(),
) -> None:
    """dataclass / 对象属性 / Mapping 键名对齐 ORM 列后 setattr。"""
    names = _mapped_column_names(type(instance))
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if not isinstance(key, str) or key in skip or key not in names:
                continue
            setattr(instance, key, value)
        return
    for name in names:
        if name in skip or not hasattr(payload, name):
            continue
        setattr(instance, name, getattr(payload, name))


def apply_dto_fields(
    instance: object,
    dto: object,
    *,
    skip: frozenset[str] = frozenset(),
) -> None:
    """只写入 Pydantic v2 已显式设置的字段（exclude_unset）。"""
    fields_set = getattr(dto, "model_fields_set", None)
    if not isinstance(fields_set, set | frozenset):
        apply_payload_fields(instance, dto, skip=skip)
        return
    names = _mapped_column_names(type(instance))
    for name in fields_set:
        if not isinstance(name, str) or name in skip or name not in names:
            continue
        setattr(instance, name, getattr(dto, name))


def query_update(query: Query[T], values: Mapping[str, object]) -> int:
    """批量 UPDATE；集中绕过 SQLAlchemy stubs 对 dict[..., Any] 的要求。"""
    return int(query.update(dict(values), synchronize_session=False))  # type: ignore[arg-type]
