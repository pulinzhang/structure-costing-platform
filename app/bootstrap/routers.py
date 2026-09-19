"""扫描并注册 app.routers 下的 APIRouter。

扫描必须看得见。启动日志要能回答：扫到了谁、prefix 是什么、
变量是不是叫 router、有没有因 re-export 被当成重复跳过。
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter, FastAPI

import app.routers as routers_package
from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.routers")


def include_scanned_routers(app: FastAPI) -> None:
    routers = _collect_routers(routers_package)
    for router in routers:
        app.include_router(router)
    logger.info("共注册 %d 个 router", len(routers))


def _collect_routers(package: ModuleType) -> list[APIRouter]:
    seen: set[int] = set()
    found: list[APIRouter] = []
    _scan_package(package, seen, found)
    return found


def _scan_package(package: ModuleType, seen: set[int], found: list[APIRouter]) -> None:
    # 字母序扫描、不重排。路径硬约束（/{id:int}）见 api-type-safety.mdc §6
    # 与 scripts/check_route_path_params.py；此处不靠文件名抢优先级。
    for name, is_package in _iter_child_modules(package):
        # import_module 会执行模块顶层。扫描能成立的前提：router 顶层只 import schema / service
        # （及 FastAPI/deps），禁止 import main 或入口 app 实例，否则循环导入。
        module = importlib.import_module(name)
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            _accept_or_skip(name, router, seen, found)
        elif not is_package:
            _warn_if_router_misnamed(name, module)
        if is_package:
            _scan_package(module, seen, found)


def _iter_child_modules(package: ModuleType) -> list[tuple[str, bool]]:
    pkg_prefix = f"{package.__name__}."
    children: list[tuple[str, bool]] = []
    seen_short: set[str] = set()
    for _finder, name, is_package in pkgutil.iter_modules(package.__path__, pkg_prefix):
        seen_short.add(name.removeprefix(pkg_prefix))
        children.append((name, is_package))
    for extra in _packages_missing_init(package, seen_short):
        logger.warning(
            "包 %s 缺少 __init__.py，pkgutil.iter_modules 扫不到；已兜底导入，请补包标记",
            extra,
        )
        children.append((extra, True))
    return children


def _packages_missing_init(package: ModuleType, already: set[str]) -> list[str]:
    missing: list[str] = []
    for path_entry in package.__path__:
        root = Path(path_entry)
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or child.name == "__pycache__":
                continue
            if child.name in already:
                continue
            has_py = any(
                item.is_file() and item.suffix == ".py" and item.name != "__init__.py"
                for item in child.iterdir()
            )
            if has_py:
                missing.append(f"{package.__name__}.{child.name}")
    return missing


def _accept_or_skip(
    module_name: str,
    router: APIRouter,
    seen: set[int],
    found: list[APIRouter],
) -> None:
    _warn_if_prefix_missing(module_name, router)
    # 同一对象若被包 __init__ re-export，用 id 去重。规范已禁止 re-export，此处只作兜底。
    router_id = id(router)
    if router_id in seen:
        logger.info("跳过重复 router: %s（同一对象已注册）", module_name)
        return
    seen.add(router_id)
    found.append(router)
    logger.info(
        "扫描到 router: %s prefix=%s",
        module_name,
        router.prefix or "(空)",
    )


def _warn_if_router_misnamed(module_name: str, module: ModuleType) -> None:
    """叶子模块里有 APIRouter 却不叫 router：扫描认不到。"""
    aliases = [
        key
        for key, value in vars(module).items()
        if isinstance(value, APIRouter) and key != "router" and not key.startswith("_")
    ]
    if not aliases:
        return
    logger.warning(
        "模块 %s 有 APIRouter 但未命名为 router（现有: %s），扫描只认 router",
        module_name,
        ", ".join(sorted(aliases)),
    )


def _warn_if_prefix_missing(module_name: str, router: APIRouter) -> None:
    """空 prefix 一律违规：扫描不会再补，只留日志。"""
    if router.prefix:
        return
    logger.warning(
        "router %s 未设置 prefix，扫描不再补 prefix，请写在 APIRouter() 上",
        module_name,
    )
