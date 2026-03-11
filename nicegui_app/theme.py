"""FLOPI — 테마 (colors, CSS, 상수)."""

from nicegui import ui

# ── 색상 상수 ──

COLORS = {
    "bg": "#030712",
    "card": "rgba(17,24,39,0.6)",
    "border": "rgba(255,255,255,0.06)",
    "primary": "#10b981",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "info": "#3b82f6",
    "success": "#10b981",
    "text": "#f3f4f6",
    "muted": "#9ca3af",
    "dark_muted": "#6b7280",
}

VARIANT_COLORS = {
    "danger": COLORS["danger"],
    "warning": COLORS["warning"],
    "info": COLORS["info"],
    "success": COLORS["success"],
}

# ── 포맷 맵 ──

SEV_MAP = {"critical": "CRITICAL", "warning": "WARNING"}
SEV_COLORS = {"critical": COLORS["danger"], "warning": COLORS["warning"]}

STATUS_MAP = {"detected": "감지됨", "in_progress": "처리중", "resolved": "해결"}
STATUS_COLORS = {
    "detected": COLORS["danger"],
    "in_progress": COLORS["warning"],
    "resolved": COLORS["success"],
}

CHECK_MAP = {"threshold": "임계치", "delta": "변화율", "absence": "부재", "llm": "AI"}
CAT_MAP = {"logistics": "물류", "wip": "재공", "equipment": "설비"}

ROLE_MAP = {"admin": "관리자", "operator": "운영자", "viewer": "열람자"}

_COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*:not(.material-icons):not(.q-icon):not([class*="notranslate"]) {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* 스크롤바 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { border-radius: 3px; }

/* 애니메이션 */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeInUp 0.4s ease-out; }

@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.pulse-dot {
    width: 8px; height: 8px; border-radius: 50%;
    animation: pulse-dot 2s infinite;
}

.q-btn { border-radius: 8px !important; }
.q-tab-panels { background: transparent !important; }
"""

_DARK_CSS = """
::-webkit-scrollbar-track { background: #0a0f1a; }
::-webkit-scrollbar-thumb { background: #374151; }
::-webkit-scrollbar-thumb:hover { background: #4b5563; }

.glass-card {
    background: rgba(17,24,39,0.6) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 16px !important;
}

.q-drawer { background: linear-gradient(180deg, #0f1629 0%, #0a0f1a 100%) !important; border-right: 1px solid rgba(255,255,255,0.06) !important; }
.q-page { background: #030712 !important; }
.q-table__card { background: rgba(17,24,39,0.6) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 12px !important; }
.q-table thead th { color: #9ca3af !important; font-weight: 600 !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
.q-table tbody td { color: #e5e7eb !important; border-bottom: 1px solid rgba(255,255,255,0.04) !important; }
.q-table tbody tr:hover td { background: rgba(16,185,129,0.05) !important; }
.q-table tbody tr.selected td { background: rgba(16,185,129,0.12) !important; }
.q-field__control { background: rgba(17,24,39,0.8) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important; }
.q-field__label { color: #9ca3af !important; }
.q-field__native, .q-field__input { color: #e5e7eb !important; }
.q-dialog__inner > .q-card { background: #111827 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 16px !important; }
.q-tab { color: #9ca3af !important; }
.q-tab--active { color: #10b981 !important; }
.q-expansion-item__container { background: rgba(17,24,39,0.4) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 12px !important; }
"""

_LIGHT_CSS = """
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

.glass-card {
    background: rgba(255,255,255,0.85) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0,0,0,0.08) !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.q-drawer { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important; border-right: 1px solid rgba(0,0,0,0.08) !important; }
.q-page { background: #f8fafc !important; }
.q-table__card { background: white !important; border: 1px solid rgba(0,0,0,0.08) !important; border-radius: 12px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.q-table thead th { color: #64748b !important; font-weight: 600 !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
.q-table tbody td { color: #1e293b !important; border-bottom: 1px solid rgba(0,0,0,0.05) !important; }
.q-table tbody tr:hover td { background: rgba(16,185,129,0.05) !important; }
.q-table tbody tr.selected td { background: rgba(16,185,129,0.1) !important; }
.q-field__control { background: white !important; border: 1px solid rgba(0,0,0,0.12) !important; border-radius: 8px !important; }
.q-field__label { color: #64748b !important; }
.q-field__native, .q-field__input { color: #1e293b !important; }
.q-dialog__inner > .q-card { background: white !important; border: 1px solid rgba(0,0,0,0.1) !important; border-radius: 16px !important; }
.q-tab { color: #64748b !important; }
.q-tab--active { color: #10b981 !important; }
.q-expansion-item__container { background: rgba(241,245,249,0.8) !important; border: 1px solid rgba(0,0,0,0.06) !important; border-radius: 12px !important; }
.glass-card .q-badge { border-color: currentColor !important; }
.q-toggle__label, .q-switch__label { color: #1e293b !important; }
"""


def apply_theme(dark: bool = True):
    """NiceGUI 글로벌 테마 적용."""
    if dark:
        ui.colors(primary="#10b981", dark="#030712", dark_page="#030712")
    else:
        ui.colors(primary="#10b981")

    # 테마에 따라 COLORS 동적 갱신
    if dark:
        COLORS.update({
            "bg": "#030712", "card": "rgba(17,24,39,0.6)",
            "border": "rgba(255,255,255,0.06)",
            "text": "#f3f4f6", "muted": "#9ca3af", "dark_muted": "#6b7280",
        })
    else:
        COLORS.update({
            "bg": "#f8fafc", "card": "rgba(255,255,255,0.85)",
            "border": "rgba(0,0,0,0.08)",
            "text": "#1e293b", "muted": "#64748b", "dark_muted": "#94a3b8",
        })

    mode_css = _DARK_CSS if dark else _LIGHT_CSS
    ui.add_head_html(f"<style>{_COMMON_CSS}\n{mode_css}</style>")
