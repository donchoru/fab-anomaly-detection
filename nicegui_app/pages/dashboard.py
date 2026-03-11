"""FAB SENTINEL — 대시보드 페이지."""

from __future__ import annotations

import plotly.graph_objects as go
from nicegui import app, ui

from .. import api_client as api
from ..components import (
    CHART_LAYOUT,
    CAT_MAP,
    cycle_card,
    empty_state,
    fmt_time,
    kpi_card,
    section_header,
)
from ..theme import COLORS


@ui.refreshable
async def dashboard_content():
    try:
        overview = await api.get_overview()
        stats = await api.get_stats()
    except Exception as e:
        ui.notify(f"API 조회 실패: {e}", type="negative")
        return

    summary = overview.get("anomaly_summary", {})
    last_cycle = overview.get("last_cycle")

    # ── KPI 카드 ──
    with ui.row().classes("gap-4 flex-wrap"):
        kpi_card("🚨", summary.get("active_critical", 0), "활성 위험", "danger")
        kpi_card("⚠️", summary.get("active_warning", 0), "활성 경고", "warning")
        kpi_card("📊", summary.get("total", 0), "24H 이상", "info")
        kpi_card("📋", stats.get("active_rules", 0), "활성 규칙", "success")

    ui.separator().classes("my-4 opacity-10")

    with ui.row().classes("w-full gap-6"):
        # ── 좌: 상태 분포 (도넛) ──
        with ui.column().classes("flex-1"):
            section_header("📈", "상태 분포 (24h)")

            detected = summary.get("detected", 0)
            in_progress = summary.get("in_progress", 0)
            resolved = summary.get("resolved", 0)
            total = detected + in_progress + resolved

            if total > 0:
                fig = go.Figure(
                    go.Pie(
                        values=[detected, in_progress, resolved],
                        labels=["감지됨", "처리중", "해결"],
                        hole=0.65,
                        marker=dict(
                            colors=["#ef4444", "#f59e0b", "#10b981"],
                            line=dict(color="#030712", width=3),
                        ),
                        textinfo="label+value",
                        textfont=dict(size=13, color="white"),
                        hovertemplate="<b>%{label}</b><br>%{value}건 (%{percent})<extra></extra>",
                    )
                )
                fig.update_layout(
                    **CHART_LAYOUT,
                    height=260,
                    showlegend=False,
                    annotations=[
                        dict(
                            text=f"<b>{total}</b><br><span style='font-size:11px;color:#6b7280'>전체</span>",
                            x=0.5,
                            y=0.5,
                            font=dict(size=28, color="#e5e7eb"),
                            showarrow=False,
                        )
                    ],
                )
                ui.plotly(fig).classes("w-full")
            else:
                empty_state("✨", "감지된 이상 없음")

        # ── 우: 마지막 감지 사이클 + 최근 이상 ──
        with ui.column().classes("flex-1"):
            section_header("🔄", "마지막 감지 사이클")

            if last_cycle:
                dur = last_cycle.get("duration_ms")
                with ui.row().classes("w-full gap-3"):
                    cycle_card(last_cycle.get("rules_evaluated", 0), "규칙 평가")
                    cycle_card(last_cycle.get("anomalies_found", 0), "이상 감지")
                    cycle_card(f"{dur}ms" if dur else "-", "소요시간")
                ui.label(f"시작: {last_cycle.get('started_at', '')}").classes("text-xs mt-2").style(
                    f"color: {COLORS['dark_muted']}"
                )
            else:
                empty_state("⏳", "아직 감지 사이클이 실행되지 않았습니다")

            # 최근 이상 타임라인
            try:
                recent = await api.get_anomalies(limit=5)
                if recent:
                    section_header("⏱", "최근 이상")
                    with ui.card().classes("glass-card p-4 w-full"):
                        for a in recent[:5]:
                            sev = a.get("severity", "warning")
                            dot_color = "#ef4444" if sev == "critical" else "#f59e0b"
                            with ui.row().classes("items-center gap-3 py-2").style(
                                "border-bottom: 1px solid rgba(255,255,255,0.04)"
                            ):
                                ui.element("div").classes("pulse-dot flex-shrink-0").style(
                                    f"background: {dot_color}"
                                )
                                with ui.column().classes("gap-0"):
                                    ui.label(
                                        (a.get("title") or "")[:40]
                                    ).classes("text-sm font-medium").style(f"color: {COLORS['text']}")
                                    ui.label(
                                        f"{fmt_time(a.get('detected_at'))} · {CAT_MAP.get(a.get('category', ''), a.get('category', ''))}"
                                    ).classes("text-xs").style(f"color: {COLORS['dark_muted']}")
            except Exception:
                pass

    ui.separator().classes("my-4 opacity-10")

    # ── 수동 감지 버튼 ──
    is_admin = app.storage.user.get("role") in ("admin", "operator")
    if is_admin:

        async def on_trigger():
            try:
                result = await api.trigger_detection()
                ui.notify(
                    f"완료: {result.get('rules_evaluated', 0)}개 규칙, "
                    f"{result.get('anomalies_found', 0)}개 이상 "
                    f"({result.get('duration_ms', 0)}ms)",
                    type="positive",
                )
                dashboard_content.refresh()
            except Exception as e:
                ui.notify(f"감지 실패: {e}", type="negative")

        ui.button("⚡ 수동 감지 실행", on_click=on_trigger, color="primary")
    else:
        ui.label("수동 감지는 관리자만 가능합니다.").classes("text-sm").style(
            f"color: {COLORS['dark_muted']}"
        )


async def render():
    with ui.row().classes("w-full justify-end mb-2"):
        ui.button("🔄 새로고침", on_click=dashboard_content.refresh).props("flat dense no-caps").classes("text-xs")
    await dashboard_content()
