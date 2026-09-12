"""还原页「当时的文件」去重合并。

品类中文名在 labels.DOCUMENT_CATEGORY_LABELS。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.file_trace.upload_file_repository import UploadFileRepository
from app.schemas.vo.assembly_cost_restore_vo import RestoreDocumentRefVO
from app.services.costing.assembly_cost.restore.labels import document_category_label


class RestoreDocuments:
    def __init__(self, upload_file_repo: UploadFileRepository) -> None:
        self.upload_file_repo = upload_file_repo

    def _add_tonnage_documents(
        self,
        db: Session,
        documents: list[RestoreDocumentRefVO],
        *,
        location: str,
        year: int,
        short_code: str,
    ) -> None:
        rows = self.upload_file_repo.list_active_by_scope(
            db,
            file_category="stamping_tonnage_price",
            location=location,
            year=year,
        )
        for row in rows:
            filename = (row.original_filename or "").strip()
            if not filename:
                continue
            self._add_document(
                documents,
                file_category="stamping_tonnage_price",
                filename=filename,
                excel_row=None,
                short_code=short_code,
            )

    def _add_document(
        self,
        documents: list[RestoreDocumentRefVO],
        *,
        file_category: str,
        filename: str,
        excel_row: int | None,
        short_code: str,
    ) -> None:
        documents.append(
            RestoreDocumentRefVO(
                file_category=file_category,
                file_category_label=document_category_label(file_category),
                filename=filename,
                excel_row=excel_row,
                cited_short_codes=[short_code] if short_code else [],
            )
        )

    def _merge_documents(self, documents: list[RestoreDocumentRefVO]) -> list[RestoreDocumentRefVO]:
        grouped: dict[tuple[str, str, int | None], list[str]] = {}
        for doc in documents:
            key = (doc.file_category, doc.filename, doc.excel_row)
            codes = grouped.setdefault(key, [])
            for code in doc.cited_short_codes:
                if code not in codes:
                    codes.append(code)
        merged = [
            RestoreDocumentRefVO(
                file_category=category,
                file_category_label=document_category_label(category),
                filename=filename,
                excel_row=row,
                cited_short_codes=codes,
            )
            for (category, filename, row), codes in grouped.items()
        ]
        return sorted(merged, key=lambda doc: (doc.file_category, doc.filename, doc.excel_row or 0))
