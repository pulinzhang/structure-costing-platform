"""材料变更前缀已挂上，扫描出来的其它路径不得占用它。"""

import app.routers as routers_package
from app.bootstrap.routers import _collect_routers

_MATERIAL_PREFIX = "/api/engineering-change/material"


def test_scanned_routes_keep_material_prefix() -> None:
    routers = _collect_routers(routers_package)
    material = [router for router in routers if router.prefix == _MATERIAL_PREFIX]
    assert len(material) == 1
    paths = {getattr(route, "path", "") for route in material[0].routes}
    assert any(path.endswith("/upload") for path in paths)
    assert any("/uploads/{upload_log_id:int}" in path for path in paths)
    for router in routers:
        if router.prefix == _MATERIAL_PREFIX:
            continue
        for route in router.routes:
            full_path = f"{router.prefix}{route.path}"
            assert not full_path.startswith(_MATERIAL_PREFIX)
