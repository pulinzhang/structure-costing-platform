"""应用启动前置步骤（Schema 升级等）。"""

from app.bootstrap.schema_upgrade import run_schema_upgrade

__all__ = ["run_schema_upgrade"]
