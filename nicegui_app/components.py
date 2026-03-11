"""FAB SENTINEL — 재사용 컴포넌트."""

from __future__ import annotations

from nicegui import ui

from .theme import (
    COLORS,
    VARIANT_COLORS,
    SEV_MAP,
    SEV_COLORS,
    STATUS_MAP,
    STATUS_COLORS,
    CHECK_MAP,
    CAT_MAP,
)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#9ca3af"),
    margin=dict(l=0, r=0, t=0, b=0),
)


def fmt_time(t: str | None) -> str:
    if not t:
        return ""
    s = str(t)[:19]
    try:
        return s[5:10].replace("-", "/") + " " + s[11:16]
    except Exception:
        return s


def kpi_card(icon: str, value, label: str, variant: str):
    color = VARIANT_COLORS.get(variant, COLORS["primary"])
    with ui.card().classes("glass-card animate-in relative overflow-hidden p-5").style("width: 200px; min-width: 200px"):
        # 상단 컬러 바
        ui.element("div").classes("absolute top-0 left-0 w-full h-[3px]").style(f"background: {color}")
        # 아이콘
        with ui.element("div").classes(
            "w-11 h-11 rounded-xl flex items-center justify-center mb-3"
        ).style(f"background: {color}15"):
            ui.html(f'<span style="font-size:1.3rem">{icon}</span>')
        # 값
        ui.label(str(value)).classes("text-4xl font-extrabold leading-none").style(f"color: {color}")
        # 라벨
        ui.label(label).classes("text-xs font-semibold uppercase tracking-wider mt-1").style(
            f"color: {COLORS['dark_muted']}"
        )


def severity_badge(severity: str):
    color = SEV_COLORS.get(severity, COLORS["muted"])
    text = SEV_MAP.get(severity, severity.upper())
    ui.badge(text, color=color).props("outline").classes("text-xs font-bold")


def status_badge(status: str):
    color = STATUS_COLORS.get(status, COLORS["muted"])
    text = STATUS_MAP.get(status, status)
    ui.badge(text, color=color).props("outline").classes("text-xs font-bold")


def check_badge(check_type: str):
    text = CHECK_MAP.get(check_type, check_type)
    ui.badge(text, color=COLORS["info"]).props("outline").classes("text-xs font-bold")


def category_badge(category: str):
    text = CAT_MAP.get(category, category)
    ui.badge(text, color=COLORS["primary"]).props("outline").classes("text-xs font-bold")


def section_header(icon: str, text: str):
    with ui.row().classes("items-center gap-3 mb-4 mt-2 w-full"):
        ui.html(f'<span style="font-size:1.2rem">{icon}</span>')
        ui.label(text).classes("text-sm font-bold uppercase tracking-wider").style(
            f"color: {COLORS['text']}"
        )
        ui.element("div").classes("flex-grow h-px").style(
            "background: linear-gradient(90deg, rgba(16,185,129,0.4), transparent)"
        )


def detail_row(label: str, value):
    with ui.row().classes("w-full justify-between items-center py-2").style(
        f"border-bottom: 1px solid {COLORS['border']}"
    ):
        ui.label(label).classes("text-xs font-semibold uppercase tracking-wider").style(
            f"color: {COLORS['dark_muted']}"
        )
        ui.label(str(value)).classes("text-sm font-medium").style(f"color: {COLORS['text']}")


def cycle_card(value, label: str):
    with ui.card().classes("glass-card p-4 text-center min-w-[120px]"):
        ui.label(str(value)).classes("text-2xl font-extrabold").style(f"color: {COLORS['primary']}")
        ui.label(label).classes("text-xs font-semibold uppercase tracking-wider mt-1").style(
            f"color: {COLORS['dark_muted']}"
        )


def empty_state(icon: str, text: str):
    with ui.column().classes("items-center justify-center py-12 w-full"):
        ui.html(f'<span style="font-size:2.5rem; opacity:0.5">{icon}</span>')
        ui.label(text).classes("text-sm mt-3").style(f"color: {COLORS['dark_muted']}")
