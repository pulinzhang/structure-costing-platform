"""
开发 / 测试：清空全部用户权限后，再给非管理员写入 catalog 全量权限码。

流程：
1. 删除 ``user_permissions`` 全表（不保留历史，清掉脏码 / 已下线码）
2. 给每个非管理员覆盖写入当前 catalog 全部权限码
3. 管理员本身是 ``*``，不写表

用法（仓库根目录）::

    python -X utf8 -m scripts.grant_all_permissions_dev
    python -X utf8 -m scripts.grant_all_permissions_dev --dry-run

生产环境默认拒绝执行；确需强制时加 ``--force``（不推荐）。
"""

from __future__ import annotations

import argparse
import sys

from app.common.permissions.catalog import get_all_codes
from app.config import settings
from app.database import DatabaseConfig
from app.models.user_permission import UserPermission
from app.repositories.settings.users.user_permission_repository import (
    UserPermissionRepository,
)
from app.repositories.settings.users.user_repository import UserRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="开发测试：清空后全员授予全部业务权限")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要执行的步骤，不写库",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="允许在非 development 环境执行（危险）",
    )
    args = parser.parse_args(argv)

    env_name = (settings.ENV or "").strip().lower()
    if env_name not in {"development", "dev", "test", "testing"} and not args.force:
        print(
            f"拒绝执行：当前 ENV={settings.ENV!r}。"
            "本脚本仅用于开发/测试；若坚持请加 --force",
            file=sys.stderr,
        )
        return 1

    all_codes = sorted(get_all_codes())
    if not all_codes:
        print("catalog 无权限码，中止", file=sys.stderr)
        return 1

    user_repo = UserRepository()
    perm_repo = UserPermissionRepository()
    db = DatabaseConfig.get_session_factory()()
    try:
        existing_count = db.query(UserPermission).count()
        print(
            f"步骤 1：清空 user_permissions"
            f"{'（dry-run）' if args.dry_run else ''}，"
            f"当前 {existing_count} 行"
        )
        if not args.dry_run:
            deleted = db.query(UserPermission).delete(synchronize_session=False)
            db.flush()
            print(f"  已删除 {deleted} 行")

        users = user_repo.list_all(db)
        granted = 0
        skipped_admin = 0
        print(f"步骤 2：写入全量权限码（共 {len(all_codes)} 个）")
        for user in users:
            if user.is_admin:
                skipped_admin += 1
                print(f"  跳过管理员 id={user.id} username={user.username}")
                continue
            print(
                f"  {'[dry-run] ' if args.dry_run else ''}"
                f"授权 id={user.id} username={user.username}"
            )
            if not args.dry_run:
                perm_repo.replace_codes(db, user.id, all_codes)
            granted += 1

        if not args.dry_run:
            db.commit()

        print(
            f"完成：环境={settings.ENV}，权限码 {len(all_codes)} 个，"
            f"已授权非管理员 {granted} 人，跳过管理员 {skipped_admin} 人"
            + ("（dry-run，未写库）" if args.dry_run else "")
        )
        print("提示：已登录用户需重新登录或刷新会话后权限才会生效。")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"失败：{exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
