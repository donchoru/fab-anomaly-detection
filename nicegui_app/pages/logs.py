"""FAB SENTINEL — 감지 로그 페이지."""

from __future__ import annotations

from nicegui import ui

from .. import api_client as api
from ..components import (
    CAT_MAP,
    cycle_card,
    empty_state,
    fmt_time,
    section_header,
)
from ..theme import COLORS, SEV_MAP


@ui.refreshable
async def logs_content():
    section_header("📋", "감지 로그")

    # ── 마지막 감지 사이클 ──
    try:
        overview = await api.get_overview()
        last_cycle = overview.get("last_cycle")

        if last_cycle:
            section_header("🔄", "마지막 감지 사이클")
            dur = last_cycle.get("duration_ms")
            with ui.row().classes("w-full gap-3 flex-wrap"):
                cycle_card(last_cycle.get("rules_evaluated", 0), "규칙 평가")
                cycle_card(last_cycle.get("anomalies_found", 0), "이상 감지")
                cycle_card(f"{dur}ms" if dur else "-", "소요시간")
                cycle_card(fmt_time(last_cycle.get("started_at")), "시작시각")
        else:
            empty_state("⏳", "감지 사이클 이력이 없습니다")
    except Exception as e:
        ui.notify(f"조회 실패: {e}", type="negative")

    ui.separator().classes("my-4 opacity-10")

    # ── 최근 감지 이력 ──
    section_header("📊", "최근 감지 이력")

    try:
        anomalies = await api.get_anomalies(limit=50)
        if anomalies:
            status_labels = {"detected": "감지됨", "in_progress": "처리중", "resolved": "해결"}
            status_icons = {"detected": "🔴", "in_progress": "🔧", "resolved": "✅"}

            for status_val in ["detected", "in_progress", "resolved"]:
                filtered = [a for a in anomalies if a.get("status") == status_val]
                if not filtered:
                    continue

                ui.label(
                    f'{status_icons.get(status_val, "")} {status_labels.get(status_val, status_val)} ({len(filtered)}건)'
                ).classes("text-sm font-bold mt-4 mb-2").style(f"color: {COLORS['text']}")

                columns = [
                    {"name": "severity", "label": "심각도", "field": "severity", "align": "left", "sortable": True},
                    {"name": "title", "label": "제목", "field": "title", "align": "left", "sortable": True},
                    {"name": "category", "label": "카테고리", "field": "category", "align": "left", "sortable": True},
                    {"name": "detected_at", "label": "감지", "field": "detected_at", "align": "left", "sortable": True},
                ]
                rows = [
                    {
                        "severity": SEV_MAP.get(a.get("severity", ""), a.get("severity", "")),
                        "title": (a.get("title") or "")[:50],
                        "category": CAT_MAP.get(a.get("category", ""), a.get("category", "")),
                        "detected_at": fmt_time(a.get("detected_at")),
                    }
                    for a in filtered
                ]
                log_search = ui.input(placeholder="검색...").props("dense outlined").classes("w-full mb-1")
                log_table = ui.table(columns=columns, rows=rows).classes("w-full mb-2").props("flat bordered dense")
                log_search.bind_value_to(log_table, "filter")
        else:
            empty_state("✨", "감지된 이상이 없습니다")
    except Exception as e:
        ui.notify(f"조회 실패: {e}", type="negative")


async def render():
    with ui.row().classes("w-full justify-end mb-2"):
        ui.button("🔄 새로고침", on_click=logs_content.refresh).props("flat dense no-caps").classes("text-xs")
    await logs_content()
