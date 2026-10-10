"""
拼焊子片 Service

- 材料侧挂子片；工序仍在父件
- 写入时冗余 parent_part_number，并按「父号-N」生成 blank_part_number（可覆盖）
- 有子片时父件 is_tailor_welded=True；清空后改回 False
不含 Router / 前端。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update, display_name
from app.exceptions import BusinessException, NotFoundException
from app.models.stamping import StampingPart
from app.parsers.stamping.models.tailor_weld import TailorWeldAssemblyParsed
from app.repositories.stamping.part.repository import StampingPartRepository
from app.repositories.stamping.part.tailor_weld_blank import (
    StampingTailorWeldBlankRepository,
)
from app.schemas.dto.stamping_tailor_weld_blank_dto import (
    StampingTailorWeldBlankCreateDTO,
    StampingTailorWeldBlankItemDTO,
    StampingTailorWeldBlankReplaceDTO,
    StampingTailorWeldBlankUpdateDTO,
    TailorWeldBlankPatch,
    TailorWeldBlankWrite,
)
from app.schemas.dto.stamping_upload_dto import StampingPartPatch
from app.schemas.vo.stamping_tailor_weld_blank_vo import StampingTailorWeldBlankVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_grade_category.service import (
    SteelGradeCategoryService,
)

logger = logging.getLogger("service.stamping.tailor_weld_blank")


class StampingTailorWeldBlankService:
    """拼焊子片业务逻辑。"""

    def __init__(self) -> None:
        self.repository = StampingTailorWeldBlankRepository()
        self.part_repository = StampingPartRepository()

    @staticmethod
    def build_blank_part_number(parent_part_number: str, blank_seq: int) -> str:
        return f"{parent_part_number}-{blank_seq}"

    def _require_parent(self, db: Session, part_id: int) -> StampingPart:
        part = self.part_repository.get_by_id(db, part_id)
        if part is None:
            raise NotFoundException(f"零件不存在: id={part_id}")
        return part

    def _set_parent_tailor_flag(
        self,
        db: Session,
        part: StampingPart,
        *,
        is_tailor_welded: bool,
        current_user: UserVO,
    ) -> None:
        if part.is_tailor_welded == is_tailor_welded:
            return
        payload: StampingPartPatch = {
            "is_tailor_welded": is_tailor_welded,
            "updated_by": display_name(current_user),
        }
        self.part_repository.update(db, part.id, payload)

    def _assign_seqs(
        self,
        items: list[StampingTailorWeldBlankItemDTO],
    ) -> list[tuple[int, StampingTailorWeldBlankItemDTO]]:
        """为未指定 blank_seq 的项按顺序补号，返回 (seq, item)。"""
        used = {item.blank_seq for item in items if item.blank_seq is not None}
        next_seq = 1
        assigned: list[tuple[int, StampingTailorWeldBlankItemDTO]] = []
        for item in items:
            if item.blank_seq is not None:
                assigned.append((item.blank_seq, item))
                continue
            while next_seq in used:
                next_seq += 1
            used.add(next_seq)
            assigned.append((next_seq, item))
            next_seq += 1
        assigned.sort(key=lambda pair: pair[0])
        return assigned

    def _item_to_payload(
        self,
        *,
        part: StampingPart,
        blank_seq: int,
        item: StampingTailorWeldBlankItemDTO | StampingTailorWeldBlankCreateDTO,
        created_by: str,
        updated_by: str,
    ) -> TailorWeldBlankWrite:
        blank_part_number = item.blank_part_number or self.build_blank_part_number(
            part.part_number,
            blank_seq,
        )
        return TailorWeldBlankWrite(
            part_id=part.id,
            parent_part_number=part.part_number,
            blank_seq=blank_seq,
            blank_part_number=blank_part_number,
            material=item.material,
            thickness=item.thickness,
            part_weight=item.part_weight,
            sheet_length=item.sheet_length,
            sheet_width=item.sheet_width,
            parts_per_sheet=item.parts_per_sheet,
            sheet_type=item.sheet_type,
            remark=item.remark,
            created_by=created_by,
            updated_by=updated_by,
        )

    def list_by_part_id(
        self,
        db: Session,
        part_id: int,
    ) -> list[StampingTailorWeldBlankVO]:
        self._require_parent(db, part_id)
        blanks = self.repository.list_by_part_id(db, part_id)
        return [StampingTailorWeldBlankVO.model_validate(row) for row in blanks]

    def get_by_id(self, db: Session, blank_id: int) -> StampingTailorWeldBlankVO:
        blank = self.repository.get_by_id(db, blank_id)
        if blank is None:
            raise NotFoundException(f"拼焊子片不存在: id={blank_id}")
        return StampingTailorWeldBlankVO.model_validate(blank)

    def replace_by_part_id(
        self,
        db: Session,
        part_id: int,
        dto: StampingTailorWeldBlankReplaceDTO,
        current_user: UserVO,
    ) -> list[StampingTailorWeldBlankVO]:
        """整组替换父件下子片，并标记父件为拼焊件。"""
        part = self._require_parent(db, part_id)
        grades = SteelGradeCategoryService().bind_stored_grades(
            db, [item.material for item in dto.items]
        )
        for item, grade in zip(dto.items, grades, strict=True):
            item.material = grade
        audit = audit_create(current_user)
        payloads: list[TailorWeldBlankWrite] = []
        for blank_seq, item in self._assign_seqs(dto.items):
            payloads.append(
                self._item_to_payload(
                    part=part,
                    blank_seq=blank_seq,
                    item=item,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
            )

        try:
            blanks = self.repository.replace_by_part_id(db, part_id, payloads)
            self._set_parent_tailor_flag(
                db,
                part,
                is_tailor_welded=True,
                current_user=current_user,
            )
            db.commit()
            return [StampingTailorWeldBlankVO.model_validate(row) for row in blanks]
        except Exception:
            db.rollback()
            logger.exception("整组替换拼焊子片失败: part_id=%s", part_id)
            raise

    def create(
        self,
        db: Session,
        part_id: int,
        dto: StampingTailorWeldBlankCreateDTO,
        current_user: UserVO,
    ) -> StampingTailorWeldBlankVO:
        part = self._require_parent(db, part_id)
        exists = self.repository.get_by_part_and_seq(db, part_id, dto.blank_seq)
        if exists is not None:
            raise BusinessException(
                f"子片序号已存在: blank_seq={dto.blank_seq}（part_id={part_id}）"
            )

        item = dto.model_copy(
            update={
                "material": SteelGradeCategoryService().bind_stored_grade(db, dto.material),
            }
        )
        audit = audit_create(current_user)
        payload = self._item_to_payload(
            part=part,
            blank_seq=dto.blank_seq,
            item=item,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )
        try:
            blank = self.repository.create(db, payload)
            self._set_parent_tailor_flag(
                db,
                part,
                is_tailor_welded=True,
                current_user=current_user,
            )
            db.commit()
            db.refresh(blank)
            return StampingTailorWeldBlankVO.model_validate(blank)
        except Exception:
            db.rollback()
            logger.exception("创建拼焊子片失败: part_id=%s", part_id)
            raise

    def update(
        self,
        db: Session,
        blank_id: int,
        dto: StampingTailorWeldBlankUpdateDTO,
        current_user: UserVO,
    ) -> StampingTailorWeldBlankVO:
        blank = self.repository.get_by_id(db, blank_id)
        if blank is None:
            raise NotFoundException(f"拼焊子片不存在: id={blank_id}")

        part = self._require_parent(db, blank.part_id)
        patch: TailorWeldBlankPatch = {}
        if "blank_seq" in dto.model_fields_set and dto.blank_seq is not None:
            patch["blank_seq"] = dto.blank_seq
        if "blank_part_number" in dto.model_fields_set and dto.blank_part_number is not None:
            patch["blank_part_number"] = dto.blank_part_number
        if "material" in dto.model_fields_set:
            patch["material"] = SteelGradeCategoryService().bind_stored_grade(db, dto.material)
        if "thickness" in dto.model_fields_set:
            patch["thickness"] = dto.thickness
        if "part_weight" in dto.model_fields_set:
            patch["part_weight"] = dto.part_weight
        if "sheet_length" in dto.model_fields_set:
            patch["sheet_length"] = dto.sheet_length
        if "sheet_width" in dto.model_fields_set:
            patch["sheet_width"] = dto.sheet_width
        if "parts_per_sheet" in dto.model_fields_set:
            patch["parts_per_sheet"] = dto.parts_per_sheet
        if "sheet_type" in dto.model_fields_set:
            patch["sheet_type"] = dto.sheet_type
        if "remark" in dto.model_fields_set:
            patch["remark"] = dto.remark

        if "blank_seq" in patch and patch["blank_seq"] != blank.blank_seq:
            conflict = self.repository.get_by_part_and_seq(
                db,
                blank.part_id,
                patch["blank_seq"],
            )
            if conflict is not None and conflict.id != blank.id:
                raise BusinessException(f"子片序号已存在: blank_seq={patch['blank_seq']}")

        # 改序号且未显式传子件号时，按约定重算「父号-N」
        if "blank_seq" in patch and "blank_part_number" not in patch:
            patch["blank_part_number"] = self.build_blank_part_number(
                part.part_number,
                patch["blank_seq"],
            )

        patch["parent_part_number"] = part.part_number
        patch["updated_by"] = audit_update(current_user)["updated_by"]

        try:
            updated = self.repository.update(db, blank_id, patch)
            if updated is None:
                raise NotFoundException(f"拼焊子片不存在: id={blank_id}")
            db.commit()
            db.refresh(updated)
            return StampingTailorWeldBlankVO.model_validate(updated)
        except (NotFoundException, BusinessException):
            raise
        except Exception:
            db.rollback()
            logger.exception("更新拼焊子片失败: id=%s", blank_id)
            raise

    def delete(self, db: Session, blank_id: int, current_user: UserVO) -> None:
        blank = self.repository.get_by_id(db, blank_id)
        if blank is None:
            raise NotFoundException(f"拼焊子片不存在: id={blank_id}")

        part_id = blank.part_id
        part = self._require_parent(db, part_id)
        if not self.repository.delete(db, blank_id):
            raise NotFoundException(f"拼焊子片不存在: id={blank_id}")

        remaining = self.repository.count_by_part_id(db, part_id)
        self._set_parent_tailor_flag(
            db,
            part,
            is_tailor_welded=remaining > 0,
            current_user=current_user,
        )
        db.commit()

    def save_parsed_for_upload(
        self,
        db: Session,
        assemblies: list[TailorWeldAssemblyParsed],
        part_map: dict[str, int],
        current_user: UserVO,
    ) -> tuple[int, int, list[str]]:
        """
        上传事务内写入拼焊子片（不 commit）。

        父件须已 flush；调用方先按 part_id 清掉旧子片再写入。
        返回 (成功总成数, 子片数, 警告)。
        """
        if not assemblies:
            return 0, 0, []

        blanks = [blank for assembly in assemblies for blank in assembly.blanks]
        grades = SteelGradeCategoryService().bind_stored_grades(
            db, [blank.material for blank in blanks]
        )
        for blank, grade in zip(blanks, grades, strict=True):
            blank.material = grade

        audit = audit_create(current_user)
        warnings: list[str] = []
        payloads: list[TailorWeldBlankWrite] = []
        saved_assemblies = 0

        for assembly in assemblies:
            parent_part_number = assembly.parent_part_number
            part_id = part_map.get(parent_part_number)
            if part_id is None:
                warnings.append(f"拼焊总成 {parent_part_number} 在零件主表中不存在，已跳过")
                continue
            if assembly.blank_count < 2:
                warnings.append(f"拼焊总成 {parent_part_number} 子片不足 2 片，已跳过")
                continue

            saved_assemblies += 1
            for blank in assembly.blanks:
                blank_seq = blank.blank_seq
                payloads.append(
                    TailorWeldBlankWrite(
                        part_id=part_id,
                        parent_part_number=parent_part_number,
                        blank_seq=blank_seq,
                        blank_part_number=(
                            blank.blank_part_number
                            or self.build_blank_part_number(parent_part_number, blank_seq)
                        ),
                        material=blank.material,
                        thickness=blank.thickness,
                        part_weight=None,
                        sheet_length=blank.sheet_length,
                        sheet_width=blank.sheet_width,
                        parts_per_sheet=blank.parts_per_sheet,
                        sheet_type=blank.sheet_type,
                        remark=blank.remark,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    )
                )

        if payloads:
            self.repository.bulk_create(db, payloads)
            db.flush()

        logger.info(
            "上传写入拼焊子片: assemblies=%s blanks=%s skipped_warnings=%s",
            saved_assemblies,
            len(payloads),
            len(warnings),
        )
        return saved_assemblies, len(payloads), warnings
