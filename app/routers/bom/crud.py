"""BOM 路由 - 清单版本与树节点最小 CRUD"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_dto import BomNodeCreate, BomSnapshotCreate, BomSnapshotQuery
from app.schemas.vo.bom_vo import (
    BomCascadeFilterOptionsVO,
    BomCascadeFilterQuery,
    BomNodeTreeVO,
    BomNodeVO,
    BomSnapshotVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom_service import BomService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom", tags=["BOM API"])

_bom_service = BomService()

# 产品结构页、上传页、材料清单列表共享只读接口
_bom_read = require_any_perm(
    Perm.BOM_STRUCTURE_VIEW,
    Perm.BOM_UPLOAD_VIEW,
    Perm.BOM_MATERIAL_VIEW,
)
# 级联下拉：结构/上传/材料清单列表/焊接拆解/包装运输费上传均可读取
_bom_cascade_read = require_any_perm(
    Perm.BOM_STRUCTURE_VIEW,
    Perm.BOM_UPLOAD_VIEW,
    Perm.BOM_MATERIAL_VIEW,
    Perm.BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
    Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW,
    Perm.BOM_PACKAGING_TRANSPORT_FEE_UPLOAD_VIEW,
    Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW,
    Perm.BOM_PROCUREMENT_OBJECT_GENERATE,
    Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW,
    Perm.BOM_ANNUAL_PART_PRICE_UPLOAD_VIEW,
    Perm.BOM_ANNUAL_PART_PRICE_VIEW,
)


@router.get(
    "/filters/cascade",
    response_model=ApiResponse[BomCascadeFilterOptionsVO],
)
def get_bom_cascade_filters(
    query: BomCascadeFilterQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_bom_cascade_read),
) -> ApiResponse[BomCascadeFilterOptionsVO]:
    """材料清单级联筛选：基地 → 项目 → 版本"""
    options = _bom_service.get_cascade_filter_options(db, query)
    return ApiResponse.ok(data=options, message="获取成功")


@router.get(
    "/snapshots",
    response_model=ApiResponse[PageResult[BomSnapshotVO]],
)
def list_snapshots(
    query: BomSnapshotQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_bom_read),
) -> ApiResponse[PageResult[BomSnapshotVO]]:
    items, total, filters = _bom_service.paginate_snapshots(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=ApiResponse[BomSnapshotVO],
)
def get_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_bom_read),
) -> ApiResponse[BomSnapshotVO]:
    row = _bom_service.get_snapshot(db, snapshot_id)
    return ApiResponse.ok(data=row)


@router.post(
    "/snapshots",
    response_model=ApiResponse[BomSnapshotVO],
    status_code=201,
)
def create_snapshot(
    body: BomSnapshotCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_UPLOAD_UPLOAD)),
) -> ApiResponse[BomSnapshotVO]:
    row = _bom_service.create_snapshot(db, body, current_user=current_user)
    return ApiResponse.created(data=row, message="创建成功")


@router.delete(
    "/snapshots/{snapshot_id}",
    response_model=ApiResponse[None],
)
def delete_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_MATERIAL_DELETE)),
) -> ApiResponse[None]:
    _bom_service.delete_snapshot(db, snapshot_id)
    return ApiResponse.deleted(message="删除成功")


@router.get(
    "/snapshots/{snapshot_id}/nodes",
    response_model=ApiResponse[list[BomNodeVO]],
)
def list_nodes(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_bom_read),
) -> ApiResponse[list[BomNodeVO]]:
    rows = _bom_service.list_nodes_flat(db, snapshot_id)
    return ApiResponse.ok(data=rows, message=f"查询到 {len(rows)} 个节点")


@router.get(
    "/snapshots/{snapshot_id}/tree",
    response_model=ApiResponse[list[BomNodeTreeVO]],
)
def get_tree(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_bom_read),
) -> ApiResponse[list[BomNodeTreeVO]]:
    tree = _bom_service.list_nodes_tree(db, snapshot_id)
    return ApiResponse.ok(data=tree, message="获取树成功")


@router.post(
    "/snapshots/{snapshot_id}/nodes",
    response_model=ApiResponse[BomNodeVO],
    status_code=201,
)
def create_node(
    snapshot_id: int,
    body: BomNodeCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_UPLOAD_UPLOAD)),
) -> ApiResponse[BomNodeVO]:
    row = _bom_service.create_node(db, snapshot_id, body, current_user=current_user)
    return ApiResponse.created(data=row, message="节点创建成功")


@router.delete(
    "/nodes/{node_id}",
    response_model=ApiResponse[None],
)
def delete_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_UPLOAD_UPLOAD)),
) -> ApiResponse[None]:
    _bom_service.delete_node(db, node_id)
    return ApiResponse.deleted(message="节点删除成功")
