"""大类推断：按钢种名后缀/字面 hint 判断冷轧、镀锌、酸洗。"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.constants import GRADE_LABELS
from app.parsers.yishiyiyi.policy.models.policy_block import PolicyBlock


class CategoryInference:
    """块级 / 钢种级 category_name 推断。"""

    _GALVANIZED_SUFFIXES: tuple[str, ...] = ("+Z", "+ZF", "+ZM", "+ZA", "+AZ")
    _PICKLED_SUFFIXES: tuple[str, ...] = ("+A",)
    _PICKLED_GRADES: frozenset[str] = frozenset(
        {
            "SPHC",
            "SPHD",
            "SPHE",
            "SPHF",
            "SAPH370",
            "SAPH400",
            "SAPH440",
            "QStE340TM",
            "QStE380TM",
            "QStE420TM",
            "QStE460TM",
            "QStE500TM",
            "QSTE420TM",
            "QSTE460TM",
            "QSTE500TM",
            "B510L",
            "B590L",
        }
    )

    def category_from_grade_name(self, grade: str) -> str:
        """按钢种名后缀/名称推断 category。"""
        if not grade:
            return "冷轧钢"
        for suf in self._GALVANIZED_SUFFIXES:
            if grade.endswith(suf):
                return "镀锌钢"
        if grade in self._PICKLED_GRADES:
            return "酸洗钢"
        for suf in self._PICKLED_SUFFIXES:
            if grade.endswith(suf):
                return "酸洗钢"
        return "冷轧钢"

    def infer_block_category(
        self,
        sheet: Worksheet,
        block: PolicyBlock,
    ) -> str:
        """综合'字面 hint'与'grade 后缀'推断块的 category。"""
        literal_cat = block.get("category_name") or "冷轧钢"
        if literal_cat != "冷轧钢":
            return literal_cat

        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        grade_col = block.get("grade_col", 1)
        galvanized = pickled = cold = 0
        for r in range(data_start, data_end + 1):
            v = sheet.cell(row=r, column=grade_col).value
            if v is None:
                continue
            t = str(v).strip()
            # 钢种列 "B250P1//HC260Y" 可能是操作人员笔误，将 "//" 替换为 "/"
            if "//" in t:
                t = t.replace("//", "/")
            if not t or t in GRADE_LABELS:
                continue
            cat = self.category_from_grade_name(t)
            if cat == "镀锌钢":
                galvanized += 1
            elif cat == "酸洗钢":
                pickled += 1
            else:
                cold += 1

        if galvanized and not cold:
            return "镀锌钢"
        if pickled and not cold:
            return "酸洗钢"
        if galvanized and cold:
            if galvanized > cold:
                return "镀锌钢"
            if pickled > cold:
                return "酸洗钢"
            return "冷轧钢"
        if pickled and cold:
            return "酸洗钢" if pickled > cold else "冷轧钢"
        return "冷轧钢"
