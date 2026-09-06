"""从 catalog.json 生成 codes.py。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "app" / "common" / "permissions" / "catalog.json"
OUT = ROOT / "app" / "common" / "permissions" / "codes.py"


def walk(nodes: list, out: list) -> None:
    for node in nodes:
        out.append(
            (
                node["code"],
                node.get("label") or "",
                node.get("type") or "",
            )
        )
        walk(node.get("children") or [], out)


def to_const(code: str) -> str:
    if code.startswith("op:"):
        body = code[3:]
        prefix = ""
    elif code.startswith("menu:"):
        body = code[5:]
        prefix = "MENU_"
    else:
        body = code
        prefix = ""
    return prefix + body.replace("-", "_").replace(":", "_").upper()


def main() -> None:
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    items: list[tuple[str, str, str]] = []
    walk(raw["tree"], items)

    lines = [
        '"""权限码常量：与 catalog.json 一一对应。',
        "",
        "路由 / Service 只引用 Perm.*，禁止散落字面量。",
        "启动时由 catalog.assert_codes_synced() 校验双向一致。",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from collections.abc import Iterator",
        "",
        "",
        "class Perm:",
        '    """权限码常量（值 = catalog.json 中的 code）。"""',
        "",
    ]

    for code, label, typ in items:
        name = to_const(code)
        if typ in ("menu", "group") and lines[-1] != "":
            lines.append("")
        comment = f"  # {label}" if label else ""
        lines.append(f'    {name} = "{code}"{comment}')

    lines.extend(
        [
            "",
            "",
            "def iter_perm_codes() -> Iterator[str]:",
            '    """遍历 Perm 上全部权限码字符串。"""',
            "    for name, value in vars(Perm).items():",
            '        if name.startswith("_") or not isinstance(value, str):',
            "            continue",
            "        yield value",
            "",
            "",
            "def get_perm_code_map() -> dict[str, str]:",
            '    """常量名 → code。"""',
            "    return {",
            "        name: value",
            "        for name, value in vars(Perm).items()",
            '        if not name.startswith("_") and isinstance(value, str)',
            "    }",
            "",
        ]
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(items)} codes)")


if __name__ == "__main__":
    main()
