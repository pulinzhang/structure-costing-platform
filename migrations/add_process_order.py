"""
数据库迁移脚本 - 添加 process_order 列到 stamping_processes 表
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import DatabaseConfig

def migrate():
    """添加缺失的 process_order 列"""
    engine = DatabaseConfig.get_engine()
    with engine.connect() as conn:
        # 检查列是否存在
        result = conn.execute(text("PRAGMA table_info(stamping_processes)"))
        columns = [row[1] for row in result]

        if "process_order" not in columns:
            print("添加 process_order 列到 stamping_processes 表...")
            conn.execute(text("ALTER TABLE stamping_processes ADD COLUMN process_order INTEGER NOT NULL DEFAULT 1"))
            conn.commit()
            print("完成！")
        else:
            print("process_order 列已存在，无需迁移。")

if __name__ == "__main__":
    migrate()
