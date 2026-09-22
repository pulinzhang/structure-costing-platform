"""工程变更编排上下文类型。"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.parsers.bom.bom_parser import BomParsedNode
from app.parsers.engineering_change.design_change.change_order_parser import ChangeOrderRowParsed
from app.repositories.engineering_change.design_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.services.async_task.worker_runner import ProgressCallback

__all__ = [
    "EngineeringChangeExecuteArgs",
    "PipelineBundle",
    "PreparedChangeOrder",
    "PreparedBundle",
    "ProgressCallback",
    "report_progress",
]


@dataclass(slots=True)
class EngineeringChangeExecuteArgs:
    """工程变更 execute 入参（避免指挥家主方法被 kwargs 撑破行数）。"""

    log_id: int
    upload_file_id: int
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    file_content: bytes


@dataclass(slots=True)
class PreparedChangeOrder:
    """变更单一行 + 定位到的变更前总成。"""

    change_order: ChangeOrderRowParsed
    before_root_id: int
    before_seq_no: int | None
    snapshot_id: int
    sliced_bom_nodes: list[BomParsedNode] | None


@dataclass(slots=True)
class PreparedBundle:
    log_id: int
    upload_file_id: int
    location: str
    vehicle_model: str
    customer_name: str
    effective_year: int
    effective_month: int
    change_orders: list[PreparedChangeOrder]
    file_content: bytes
    project_expiry_year: int | None = None
    project_expiry_month: int | None = None
    node_bom_version: str | None = None
    revise_old_to_new: dict[str, str] = field(default_factory=dict)
    part_change_order_index: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineBundle:
    not_install_count: int
    process_inserted_count: int
    die_inserted_count: int
    procurement_inserted_count: int
    breakdown_inserted_count: int
    has_bom_assembly: bool
    effect_links: list[EngineeringChangeEffectLinkInsert]
    warnings: list[str]


def report_progress(on_progress: ProgressCallback | None, progress: int, message: str) -> None:
    if on_progress is not None:
        on_progress(progress, message)
