"""FAB SENTINEL — 이상 목록 페이지."""

from __future__ import annotations

import json

from nicegui import app, ui

from .. import api_client as api
from ..components import (
    CAT_MAP,
    detail_row,
    empty_state,
    fmt_time,
    section_header,
    severity_badge,
    status_badge,
)
from ..theme import COLORS, SEV_MAP, STATUS_MAP

RCA_STATUS_MAP = {"pending": "대기중", "processing": "분석중", "done": "완료", "failed": "실패"}
RCA_STATUS_COLORS = {
    "pending": COLORS["muted"],
    "processing": COLORS["warning"],
    "done": COLORS["success"],
    "failed": COLORS["danger"],
}
CAUSE_CAT_MAP = {
    "equipment": "설비",
    "process": "공정",
    "material": "자재",
    "human": "인적",
    "environment": "환경",
    "logistics": "물류",
}

# ── 모듈 상태 ──
_selected_id: dict[str, int | None] = {"value": None}
_status_filter: dict[str, str] = {"value": "전체"}


def _render_rca_card(rca: dict):
    """RCA 분석 결과 카드 렌더링."""
    rca_status = rca.get("status", "pending")
    section_header("🔬", "원인분석 (RCA)")

    with ui.card().classes("glass-card animate-in p-5 w-full"):
        # 상태 + 신뢰도
        with ui.row().classes("gap-2 mb-3 items-center"):
            rca_color = RCA_STATUS_COLORS.get(rca_status, COLORS["muted"])
            rca_label = RCA_STATUS_MAP.get(rca_status, rca_status)
            ui.badge(rca_label, color=rca_color).props("outline").classes("text-xs font-bold")
            cause_cat = rca.get("cause_category", "")
            if cause_cat:
                cat_label = CAUSE_CAT_MAP.get(cause_cat, cause_cat)
                ui.badge(cat_label, color=COLORS["info"]).props("outline").classes("text-xs font-bold")
            confidence = rca.get("confidence")
            if confidence is not None:
                pct = int(confidence * 100)
                conf_color = COLORS["success"] if pct >= 70 else COLORS["warning"] if pct >= 40 else COLORS["danger"]
                ui.badge(f"신뢰도 {pct}%", color=conf_color).props("outline").classes("text-xs font-bold")

        # 근본 원인
        root_cause = rca.get("root_cause")
        if root_cause:
            ui.label("근본 원인").classes("text-xs font-semibold uppercase tracking-wider mt-2").style(
                f"color: {COLORS['dark_muted']}"
            )
            ui.label(root_cause).classes("text-sm font-medium mt-1").style(f"color: {COLORS['text']}")

        # 기여 요인
        factors = rca.get("contributing_factors")
        if factors:
            try:
                factor_list = json.loads(factors) if isinstance(factors, str) else factors
            except (json.JSONDecodeError, TypeError):
                factor_list = [str(factors)]
            if factor_list:
                ui.label("기여 요인").classes("text-xs font-semibold uppercase tracking-wider mt-3").style(
                    f"color: {COLORS['dark_muted']}"
                )
                for f in factor_list:
                    with ui.row().classes("items-start gap-2 mt-1"):
                        ui.html('<span style="color:#f59e0b">▸</span>')
                        ui.label(str(f)).classes("text-sm").style(f"color: {COLORS['text']}")

        # 근거
        evidence = rca.get("evidence")
        if evidence:
            try:
                ev_list = json.loads(evidence) if isinstance(evidence, str) else evidence
            except (json.JSONDecodeError, TypeError):
                ev_list = [str(evidence)]
            if ev_list:
                ui.label("분석 근거").classes("text-xs font-semibold uppercase tracking-wider mt-3").style(
                    f"color: {COLORS['dark_muted']}"
                )
                for e in ev_list:
                    with ui.row().classes("items-start gap-2 mt-1"):
                        ui.html('<span style="color:#3b82f6">•</span>')
                        ui.label(str(e)).classes("text-xs").style(f"color: {COLORS['muted']}")

        # 권장 조치
        recs = rca.get("recommendations")
        if recs:
            try:
                rec_list = json.loads(recs) if isinstance(recs, str) else recs
            except (json.JSONDecodeError, TypeError):
                rec_list = [str(recs)]
            if rec_list:
                ui.label("권장 조치").classes("text-xs font-semibold uppercase tracking-wider mt-3").style(
                    f"color: {COLORS['dark_muted']}"
                )
                for i, r in enumerate(rec_list, 1):
                    with ui.row().classes("items-start gap-2 mt-1"):
                        ui.html(f'<span style="color:#10b981; font-weight:700">{i}.</span>')
                        ui.label(str(r)).classes("text-sm").style(f"color: {COLORS['text']}")

        # 분석 시간
        analyzed_at = rca.get("analyzed_at")
        dur = rca.get("analysis_duration_ms")
        if analyzed_at or dur:
            with ui.row().classes("mt-3 gap-4"):
                if analyzed_at:
                    ui.label(f"분석 시각: {fmt_time(analyzed_at)}").classes("text-xs").style(
                        f"color: {COLORS['dark_muted']}"
                    )
                if dur:
                    ui.label(f"소요시간: {dur}ms").classes("text-xs").style(
                        f"color: {COLORS['dark_muted']}"
                    )


@ui.refreshable
async def anomaly_detail():
    anomaly_id = _selected_id["value"]
    if anomaly_id is None:
        empty_state("👈", "좌측 목록에서 이상을 선택하세요")
        return

    try:
        anomalies = await api.get_anomalies(limit=200)
        a = next((x for x in anomalies if x.get("anomaly_id") == anomaly_id), None)
    except Exception:
        a = None

    if not a:
        empty_state("❌", "이상 정보를 찾을 수 없습니다")
        return

    sev = a.get("severity", "warning")
    status_val = a.get("status", "detected")

    with ui.card().classes("glass-card animate-in p-5 w-full"):
        with ui.row().classes("gap-2 mb-4"):
            severity_badge(sev)
            status_badge(status_val)

        ui.label(a.get("title", "")).classes("text-lg font-bold mb-4").style(f"color: {COLORS['text']}")

        detail_row("카테고리", CAT_MAP.get(a.get("category", ""), a.get("category", "")))
        detail_row("영향 대상", a.get("affected_entity", "") or "-")
        detail_row("감지 시각", a.get("detected_at", "")[:19] if a.get("detected_at") else "-")
        detail_row("측정값", a.get("measured_value", "N/A"))
        detail_row("임계치", a.get("threshold_value", "N/A"))

    desc = a.get("description", "")
    if desc:
        ui.label(f"설명: {desc}").classes("text-sm mt-3").style(f"color: {COLORS['muted']}")

    analysis = a.get("llm_analysis")
    if analysis:
        section_header("🤖", "AI 분석")
        ui.markdown(analysis).classes("text-sm").style(f"color: {COLORS['text']}")

    suggestion = a.get("llm_suggestion")
    if suggestion:
        section_header("💡", "AI 제안")
        try:
            actions = json.loads(suggestion) if isinstance(suggestion, str) else suggestion
            if isinstance(actions, list):
                for i, act in enumerate(actions, 1):
                    ui.label(f"{i}. {act}").classes("text-sm").style(f"color: {COLORS['text']}")
            else:
                ui.label(str(suggestion)).classes("text-sm").style(f"color: {COLORS['text']}")
        except (json.JSONDecodeError, TypeError):
            ui.label(str(suggestion)).classes("text-sm").style(f"color: {COLORS['text']}")

    # ── RCA (원인분석) ──
    rca = await api.get_rca(anomaly_id)
    if rca:
        _render_rca_card(rca)

    # ── 상태 전이 버튼 ──
    is_admin = app.storage.user.get("role") in ("admin", "operator")
    if is_admin:
        with ui.row().classes("w-full gap-3 mt-4"):
            if status_val == "detected":

                async def start_progress():
                    try:
                        await api.update_anomaly_status(anomaly_id, "in_progress")
                        ui.notify("처리 시작", type="positive")
                        anomaly_list.refresh()
                        anomaly_detail.refresh()
                    except Exception as e:
                        ui.notify(str(e), type="negative")

                ui.button("🔧 처리 시작", on_click=start_progress, color="warning").classes("flex-1")

            if status_val in ("detected", "in_progress"):

                async def resolve():
                    try:
                        await api.update_anomaly_status(anomaly_id, "resolved", resolved_by=app.storage.user.get("username", "dashboard"))
                        ui.notify("해결 완료", type="positive")
                        anomaly_list.refresh()
                        anomaly_detail.refresh()
                    except Exception as e:
                        ui.notify(str(e), type="negative")

                ui.button("✅ 해결", on_click=resolve, color="positive").classes("flex-1")


@ui.refreshable
async def anomaly_list():
    section_header("🚨", "이상 목록")

    # 필터 라디오
    filter_options = {
        "전체": "전체",
        "detected": "🔴 감지됨",
        "in_progress": "🔧 처리중",
        "resolved": "✅ 해결",
    }

    def on_filter_change(e):
        _status_filter["value"] = e.value
        _selected_id["value"] = None
        anomaly_list.refresh()
        anomaly_detail.refresh()

    ui.toggle(
        filter_options,
        value=_status_filter["value"],
        on_change=on_filter_change,
    ).classes("mb-4")

    # 데이터 로드
    try:
        sf = _status_filter["value"]
        if sf == "전체":
            anomalies = await api.get_anomalies(limit=200)
        else:
            anomalies = await api.get_anomalies(status=sf, limit=200)
    except Exception as e:
        ui.notify(f"API 조회 실패: {e}", type="negative")
        return

    if not anomalies:
        empty_state("✨", "해당 상태의 이상이 없습니다")
        return

    ui.label(f"{len(anomalies)}건").classes("text-sm font-bold mb-2").style(f"color: {COLORS['muted']}")

    columns = [
        {"name": "severity", "label": "심각도", "field": "severity", "align": "left", "sortable": True},
        {"name": "title", "label": "제목", "field": "title", "align": "left", "sortable": True},
        {"name": "status", "label": "상태", "field": "status", "align": "left", "sortable": True},
        {"name": "detected_at", "label": "감지", "field": "detected_at", "align": "left", "sortable": True},
    ]
    rows = [
        {
            "id": a.get("anomaly_id"),
            "severity": SEV_MAP.get(a.get("severity", ""), a.get("severity", "")),
            "title": (a.get("title") or "")[:45],
            "status": STATUS_MAP.get(a.get("status", ""), a.get("status", "")),
            "detected_at": fmt_time(a.get("detected_at")),
        }
        for a in anomalies
    ]

    search = ui.input(placeholder="검색...").props("dense outlined").classes("w-full mb-2")
    table = ui.table(
        columns=columns,
        rows=rows,
        row_key="id",
    ).classes("w-full")
    table.props("flat bordered dense")
    search.bind_value_to(table, "filter")

    def on_row_click(e):
        row = e.args[1]
        _selected_id["value"] = row.get("id")
        anomaly_detail.refresh()

    table.on("row-click", on_row_click)


async def render():
    with ui.row().classes("w-full justify-end mb-2"):
        ui.button("🔄 새로고침", on_click=anomaly_list.refresh).props("flat dense no-caps").classes("text-xs")
    with ui.row().classes("w-full gap-6"):
        with ui.column().classes("flex-1"):
            await anomaly_list()
        with ui.column().classes("flex-1"):
            await anomaly_detail()
