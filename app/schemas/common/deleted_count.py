from pydantic import BaseModel


class DeletedCountVO(BaseModel):
    """清空 / 批量删除后返回删除条数。"""

    deleted_count: int = 0
