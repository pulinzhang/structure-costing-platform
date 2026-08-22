"""使用帮助专用 Actions（业务页 + /helper/ 深链）。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.llm.analysis_snapshot import AnalysisAction
from app.services.llm.usage.corpus import CorpusChunk

_TOPIC_MENU: dict[str, tuple[str, str]] = {
    "engine": ("costing", "打开自动核价引擎"),
    "export": ("l0-assembly-cost", "打开成品核价一览"),
    "faq_permission": ("settings-users", "打开用户管理"),
    "faq_stuck": ("costing", "打开自动核价引擎"),
    "upload": ("stamping-upload", "打开工艺文件上传"),
    "bom_material": ("bom-material", "打开材料清单列表"),
    "monthly": ("costing", "打开自动核价引擎"),
    "list_usage": ("l0-assembly-cost", "打开成品核价一览"),
    "menu": ("dashboard", "打开仪表盘"),
    "start": ("dashboard", "打开仪表盘"),
    "faq": ("index.html", "打开帮助入口"),
}

_TOPIC_HELP_ANCHOR: dict[str, str] = {
    "engine": "engine",
    "export": "export",
    "faq_permission": "faq",
    "faq_stuck": "faq",
    "menu": "menu",
    "start": "start",
    "monthly": "month",
    "upload": "menu",
    "bom_material": "menu",
    "list_usage": "start",
    "faq": "faq",
}


def build_usage_help_actions(
    query: AnalysisQuery,
    chunks: list[CorpusChunk],
) -> list[AnalysisAction]:
    topic = query.help_topic or "start"
    actions: list[AnalysisAction] = []
    seen_targets: set[str] = set()

    menu_hash, menu_label = _TOPIC_MENU.get(topic, ("dashboard", "打开系统"))
    if menu_hash.endswith(".html"):
        menu_target = f"/helper/{menu_hash}"
    else:
        menu_target = f"#/{menu_hash}"
    if menu_target not in seen_targets:
        actions.append(
            AnalysisAction(
                action_id=f"open_{menu_hash.replace('-', '_')}",
                type="NAVIGATE",
                label=menu_label,
                target=menu_target,
                permission="op:llm-analysis:view",
            )
        )
        seen_targets.add(menu_target)

    anchor = _TOPIC_HELP_ANCHOR.get(topic)
    primary = next((chunk for chunk in chunks if chunk.chunk_id == topic), None)
    if primary is not None:
        help_url = primary.help_url
    elif anchor:
        page = "knowledge.html" if topic == "monthly" else "help.html"
        help_url = f"/helper/{page}#{anchor}"
    else:
        help_url = "/helper/help.html"

    if help_url not in seen_targets:
        actions.append(
            AnalysisAction(
                action_id="open_help_doc",
                type="NAVIGATE",
                label="查看操作说明",
                target=help_url,
                permission="op:llm-analysis:view",
            )
        )
        seen_targets.add(help_url)

    for chunk in chunks:
        if chunk.menu_hash and chunk.chunk_id != topic:
            extra_target = f"#/{chunk.menu_hash}"
            if extra_target in seen_targets:
                continue
            actions.append(
                AnalysisAction(
                    action_id=f"open_related_{chunk.chunk_id}",
                    type="NAVIGATE",
                    label=f"打开{chunk.title}",
                    target=extra_target,
                    permission="op:llm-analysis:view",
                )
            )
            seen_targets.add(extra_target)
        if len(actions) >= 4:
            break

    return actions
