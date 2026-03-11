"""FAB SENTINEL — 규칙 관리 페이지."""

from __future__ import annotations

import json

from nicegui import app, ui

from .. import api_client as api
from ..components import (
    CAT_MAP,
    CHECK_MAP,
    detail_row,
    empty_state,
    category_badge,
    check_badge,
    section_header,
)
from ..theme import COLORS

# ── 모듈 상태 ──
_selected_id: dict[str, int | None] = {"value": None}


@ui.refreshable
async def rule_detail():
    rule_id = _selected_id["value"]
    if rule_id is None:
        empty_state("👈", "좌측 목록에서 규칙을 선택하세요")
        return

    try:
        rules = await api.get_rules(include_disabled=True)
        r = next((x for x in rules if x.get("rule_id") == rule_id), None)
        tool_catalog = await api.get_tool_catalog()
    except Exception:
        r = None
        tool_catalog = {}

    if not r:
        empty_state("❌", "규칙 정보를 찾을 수 없습니다")
        return

    is_tool = r.get("source_type") == "tool"
    ct = r.get("check_type", "threshold")
    tool_label = ""
    if is_tool and r.get("tool_name") in tool_catalog:
        tool_label = tool_catalog[r["tool_name"]]["label"]

    with ui.card().classes("glass-card animate-in p-5 w-full"):
        with ui.row().classes("gap-2 mb-4"):
            category_badge(r.get("category", ""))
            check_badge(ct)
            src_label = "TOOL" if is_tool else "SQL"
            color = COLORS["success"] if is_tool else COLORS["warning"]
            ui.badge(src_label, color=color).props("outline").classes("text-xs font-bold")

        ui.label(r.get("rule_name", "")).classes("text-lg font-bold mb-4").style(
            f"color: {COLORS['text']}"
        )

        detail_row(
            "데이터 소스",
            f"🔧 {tool_label} ({r.get('tool_name', '')})" if is_tool else "📝 SQL 쿼리",
        )
        if is_tool:
            detail_row("감시 컬럼", r.get("tool_column") or "-")
        if ct != "llm":
            detail_row("연산자", r.get("threshold_op", ">"))
            detail_row("경고 임계치", r.get("warning_value", "-"))
            detail_row("위험 임계치", r.get("critical_value", "-"))
        detail_row("LLM 판단", "🟢 활성화" if r.get("llm_enabled") else "⚪ 비활성화")
        detail_row("작성자", r.get("created_by") or "-")
        if r.get("updated_by"):
            detail_row("수정자", r.get("updated_by"))

    if r.get("llm_prompt"):
        ui.label(f"AI 조건: {r['llm_prompt']}").classes("text-sm mt-3").style(
            f"color: {COLORS['muted']}"
        )

    if not is_tool and r.get("query_template"):
        ui.code(r["query_template"], language="sql").classes("mt-3 w-full")

    is_admin = app.storage.user.get("role") in ("admin", "operator")
    if is_admin:
        # ── 활성화/비활성화 토글 ──
        is_enabled = bool(r.get("enabled", 1))

        async def toggle_enabled(e):
            try:
                await api.update_rule(rule_id, {"enabled": e.value, "updated_by": app.storage.user.get("username")})
                ui.notify("활성화" if e.value else "비활성화", type="positive")
                rule_list.refresh()
            except Exception as ex:
                ui.notify(f"변경 실패: {ex}", type="negative")

        with ui.row().classes("w-full items-center gap-3 mt-4"):
            ui.switch("규칙 활성화", value=is_enabled, on_change=toggle_enabled)

        with ui.row().classes("w-full gap-3 mt-2"):

            async def on_test():
                try:
                    result = await api.test_rule(rule_id)
                    with ui.dialog() as dlg, ui.card().classes("min-w-[500px]"):
                        ui.label("테스트 결과").classes("text-lg font-bold mb-2")
                        ui.code(json.dumps(result, ensure_ascii=False, indent=2), language="json")
                        ui.button("닫기", on_click=dlg.close)
                    dlg.open()
                except Exception as e:
                    ui.notify(f"테스트 실패: {e}", type="negative")

            ui.button("🧪 테스트", on_click=on_test).classes("flex-1")

            async def on_delete():
                try:
                    await api.delete_rule(rule_id)
                    ui.notify("삭제 완료", type="positive")
                    _selected_id["value"] = None
                    rule_list.refresh()
                    rule_detail.refresh()
                except Exception as e:
                    ui.notify(f"삭제 실패: {e}", type="negative")

            ui.button("🗑 삭제", on_click=on_delete, color="red").classes("flex-1")


@ui.refreshable
async def rule_list():
    section_header("⚙️", "규칙 관리")

    is_admin = app.storage.user.get("role") in ("admin", "operator")

    # ── 도구 카탈로그 ──
    try:
        tool_catalog = await api.get_tool_catalog()
    except Exception:
        tool_catalog = {}

    # ── 규칙 추가 (관리자) ──
    if is_admin and tool_catalog:
        tool_opts = {k: f"{v['label']} ({k})" for k, v in tool_catalog.items()}
        tool_keys = list(tool_opts.keys())

        with ui.expansion("➕ 새 규칙 추가").classes("w-full mb-4"):
            with ui.tabs().classes("w-full") as tabs:
                tab_threshold = ui.tab("조건 감시").props("no-caps")
                tab_ai = ui.tab("AI 판단").props("no-caps")

            with ui.tab_panels(tabs, value=tab_threshold).classes("w-full"):
                # ── 탭1: 조건 감시 ──
                with ui.tab_panel(tab_threshold):
                    ui.label("도구를 연결하고, 감시 조건을 설정합니다.").classes("text-xs mb-3").style(
                        f"color: {COLORS['muted']}"
                    )

                    th_tool = ui.select(
                        label="감시 도구 *",
                        options=tool_opts,
                        value=tool_keys[0] if tool_keys else None,
                    ).classes("w-full mb-2")

                    check_type_opts = {
                        "threshold": "임계치 초과",
                        "delta": "변화율 초과",
                        "absence": "데이터 부재",
                    }
                    th_check_type = ui.select(
                        label="감시 유형 *",
                        options=check_type_opts,
                        value="threshold",
                    ).classes("w-full mb-2")

                    th_name = ui.input(label="규칙명 *", placeholder="예: 컨베이어 부하율 과부하").classes(
                        "w-full mb-2"
                    )

                    th_column = ui.select(label="감시 컬럼 *", options=[]).classes("w-full mb-2")

                    def update_columns():
                        tool_info = tool_catalog.get(th_tool.value, {})
                        cols = tool_info.get("columns", [])
                        col_opts = {c["name"]: f"{c['label']} ({c['name']})" for c in cols}
                        th_column.options = col_opts
                        th_column.value = list(col_opts.keys())[0] if col_opts else None
                        th_column.update()

                    th_tool.on_value_change(lambda _: update_columns())
                    update_columns()

                    with ui.row().classes("w-full gap-3 mb-2"):
                        th_op = ui.select(label="조건", options=[">", "<", ">=", "<="], value=">").classes(
                            "flex-1"
                        )
                        th_warn = ui.number(label="경고 임계치 *", value=0.0, format="%.2f").classes(
                            "flex-1"
                        )
                        th_crit = ui.number(label="위험 임계치 *", value=0.0, format="%.2f").classes(
                            "flex-1"
                        )

                    async def submit_threshold():
                        if not th_name.value or not th_tool.value:
                            ui.notify("규칙명과 도구는 필수입니다.", type="warning")
                            return
                        tool_info = tool_catalog.get(th_tool.value, {})
                        ct = th_check_type.value
                        data = {
                            "rule_name": th_name.value,
                            "category": tool_info.get("category", "logistics"),
                            "subcategory": th_tool.value.replace("get_", ""),
                            "source_type": "tool",
                            "tool_name": th_tool.value,
                            "tool_column": th_column.value if ct != "absence" else None,
                            "check_type": ct,
                            "threshold_op": th_op.value if ct != "absence" else ">",
                            "warning_value": th_warn.value if ct != "absence" else 0.0,
                            "critical_value": th_crit.value if ct != "absence" else 0.0,
                            "eval_interval": 300,
                            "llm_enabled": 0,
                            "enabled": 1,
                            "created_by": app.storage.user.get("username"),
                        }
                        try:
                            result = await api.create_rule(data)
                            ui.notify(f"규칙 등록 완료! (ID: {result.get('rule_id', '?')})", type="positive")
                            rule_list.refresh()
                        except Exception as e:
                            ui.notify(f"등록 실패: {e}", type="negative")

                    ui.button("✅ 규칙 등록", on_click=submit_threshold, color="primary").classes(
                        "w-full mt-2"
                    )

                # ── 탭2: AI 판단 ──
                with ui.tab_panel(tab_ai):
                    ui.label(
                        "도구를 연결하고, 자연어로 이상 조건을 설명하면 AI가 판단합니다."
                    ).classes("text-xs mb-3").style(f"color: {COLORS['muted']}")

                    ui.label("💡 이렇게 설명해보세요:").classes("text-sm font-bold mb-1")
                    for hint in [
                        "특정 공정만 유독 WIP가 높으면 이상. 전체적으로 높은 건 정상.",
                        "ERROR 상태 AGV가 전체의 30%를 넘으면 위험",
                        "설비가 DOWN인데 알람이 없으면 비정상. 알람이 있으면 대응 중.",
                    ]:
                        ui.label(f"  · {hint}").classes("text-xs").style(f"color: {COLORS['dark_muted']}")

                    ai_tool = ui.select(
                        label="데이터 도구 *",
                        options=tool_opts,
                        value=tool_keys[0] if tool_keys else None,
                    ).classes("w-full mb-2 mt-3")

                    ai_name = ui.input(
                        label="규칙명 *", placeholder="예: 특정 공정만 WIP 높으면 이상"
                    ).classes("w-full mb-2")

                    ai_prompt = ui.textarea(
                        label="이상 조건 설명 *",
                        placeholder="이 데이터를 보고 이상인지 판단해줘.",
                    ).classes("w-full mb-2")

                    async def submit_ai():
                        if not ai_name.value or not ai_tool.value or not ai_prompt.value:
                            ui.notify("규칙명, 도구, 이상 조건은 필수입니다.", type="warning")
                            return
                        ai_tool_info = tool_catalog.get(ai_tool.value, {})
                        data = {
                            "rule_name": ai_name.value,
                            "category": ai_tool_info.get("category", "logistics"),
                            "subcategory": ai_tool.value.replace("get_", ""),
                            "source_type": "tool",
                            "tool_name": ai_tool.value,
                            "check_type": "llm",
                            "llm_enabled": 1,
                            "llm_prompt": ai_prompt.value,
                            "eval_interval": 300,
                            "enabled": 1,
                            "created_by": app.storage.user.get("username"),
                        }
                        try:
                            result = await api.create_rule(data)
                            ui.notify(f"규칙 등록 완료! (ID: {result.get('rule_id', '?')})", type="positive")
                            rule_list.refresh()
                        except Exception as e:
                            ui.notify(f"등록 실패: {e}", type="negative")

                    ui.button("✅ 규칙 등록", on_click=submit_ai, color="primary").classes("w-full mt-2")

    # ── 규칙 목록 ──
    try:
        rules = await api.get_rules(include_disabled=True)
    except Exception as e:
        ui.notify(f"API 조회 실패: {e}", type="negative")
        return

    if not rules:
        empty_state("📋", "등록된 규칙이 없습니다")
        return

    ui.label(f"{len(rules)}개 규칙").classes("text-sm font-bold mb-2").style(
        f"color: {COLORS['muted']}"
    )

    columns = [
        {"name": "rule_name", "label": "규칙명", "field": "rule_name", "align": "left", "sortable": True},
        {"name": "category", "label": "카테고리", "field": "category", "align": "left", "sortable": True},
        {"name": "check_type", "label": "유형", "field": "check_type", "align": "left", "sortable": True},
        {"name": "ai", "label": "AI", "field": "ai", "align": "center", "sortable": True},
        {"name": "enabled", "label": "상태", "field": "enabled", "align": "center", "sortable": True},
        {"name": "created_by", "label": "작성자", "field": "created_by", "align": "left", "sortable": True},
    ]
    rows = [
        {
            "id": r.get("rule_id"),
            "rule_name": (r.get("rule_name") or "")[:35],
            "category": CAT_MAP.get(r.get("category", ""), r.get("category", "")),
            "check_type": CHECK_MAP.get(r.get("check_type", ""), r.get("check_type", "")),
            "ai": "🟢" if r.get("llm_enabled") else "⚪",
            "enabled": "활성" if r.get("enabled") else "비활성",
            "created_by": r.get("created_by") or "-",
        }
        for r in rules
    ]

    search = ui.input(placeholder="검색...").props("dense outlined").classes("w-full mb-2")
    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
    table.props("flat bordered dense filter-method=filter")
    search.bind_value_to(table, "filter")

    def on_row_click(e):
        row = e.args[1]
        _selected_id["value"] = row.get("id")
        rule_detail.refresh()

    table.on("row-click", on_row_click)


async def render():
    with ui.row().classes("w-full gap-6"):
        with ui.column().classes("flex-1"):
            await rule_list()
        with ui.column().classes("flex-1"):
            await rule_detail()
