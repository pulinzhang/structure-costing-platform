"""权限目录与校验"""

from app.common.permissions.catalog import (
    assert_codes_synced,
    get_all_codes,
    get_defaults,
    get_mandatory,
    get_tree,
    is_valid_code,
    load_catalog,
)
from app.common.permissions.checks import (
    has_permission,
    require_admin,
    require_any_permission,
    require_permission,
)
from app.common.permissions.codes import Perm

__all__ = [
    "Perm",
    "assert_codes_synced",
    "get_all_codes",
    "get_defaults",
    "get_mandatory",
    "get_tree",
    "has_permission",
    "is_valid_code",
    "load_catalog",
    "require_admin",
    "require_any_permission",
    "require_permission",
]
