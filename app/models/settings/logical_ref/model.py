"""逻辑引用：结果表是什么、表名、过滤条件。与外键发现无关。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LogicalRef(Base):
    """删某张表时，要检查的一张计算结果表。过滤在 logical_ref_filter。"""

    __tablename__ = "logical_ref"

    deleted_table: Mapped[str] = mapped_column(String(80), primary_key=True, comment="正在删除的表")
    result_table: Mapped[str] = mapped_column(
        String(80), primary_key=True, comment="结果表表名，如 steel_prices"
    )
    result_name: Mapped[str] = mapped_column(
        String(80), nullable=False, comment="结果表是什么，如钢材联动价"
    )
    hint: Mapped[str] = mapped_column(String(200), nullable=False, comment="处理建议")


class LogicalRefFilter(Base):
    """一条过滤。生成器按 seq 用 AND 拼进结果表的 WHERE。"""

    __tablename__ = "logical_ref_filter"

    deleted_table: Mapped[str] = mapped_column(String(80), primary_key=True)
    result_table: Mapped[str] = mapped_column(String(80), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, comment="顺序")
    compare: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="eq 列相等；period_gte 账期≥；period_lte 账期≤且空值不封顶；period_before_next 早于下一行",
    )
    result_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="结果表上等值的列，如 grade"
    )
    result_year_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="结果表账期年，如 year"
    )
    result_month_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="结果表账期月，如 month"
    )
    value_table: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="过滤值所在表。空表示正在删的这一行"
    )
    value_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="等值时的取值列；账期时的年列"
    )
    value_month_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="账期时的月列"
    )
    join_from_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="被删行上用来连取值表的列"
    )
    join_to_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="取值表上被连的列"
    )
    next_table: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="下一行所在表"
    )
    next_mode: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="first 组内最早；after 严格晚于本行"
    )
    next_group_column: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="被删行上的分组列"
    )
    next_group_remote: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="下一行表上的分组列"
    )
    next_year_column: Mapped[str | None] = mapped_column(String(80), nullable=True)
    next_month_column: Mapped[str | None] = mapped_column(String(80), nullable=True)
    skip_when: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="被删行这些列任一为真则本条过滤不算"
    )
