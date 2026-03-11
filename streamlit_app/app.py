"""FAB 이상감지 대시보드 — 프리미엄 모니터링 UI."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import api_client as api

st.set_page_config(
    page_title="FAB 이상감지",
    page_icon="🏭",
    layout="wide",
)

# ══════════════════════════════════════════
# 글로벌 CSS
# ══════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── 전역 ── */
* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }
.stApp { background: #030712; }
.stApp > header { background: transparent !important; }

/* 스크롤바 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0f1a; }
::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #4b5563; }

/* ── 사이드바 ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1629 0%, #0a0f1a 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] > div { padding-top: 1rem; }

/* ── 메트릭 (숨김 - 커스텀 카드 사용) ── */
div[data-testid="stMetric"] { display: none; }

/* ── 데이터프레임 ── */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    overflow: hidden;
}
div[data-testid="stDataFrame"] [data-testid="StyledDataFrameRowCell"],
div[data-testid="stDataFrame"] [data-testid="StyledDataFrameDataCell"] {
    font-size: 0.85rem;
}

/* ── expander ── */
details {
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    background: rgba(17,24,39,0.7) !important;
    backdrop-filter: blur(20px) !important;
}

/* ── 버튼 ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(16,185,129,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 25px rgba(16,185,129,0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(55,65,81,0.5) !important;
    border: 1px solid rgba(75,85,99,0.5) !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(55,65,81,0.8) !important;
}

/* ── divider ── */
hr { border-color: rgba(255,255,255,0.06) !important; }

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(17,24,39,0.5);
    border-radius: 10px;
    padding: 4px;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}

/* ── Radio 수평 ── */
div[data-testid="stRadio"] > div { gap: 0.3rem; }
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    background: rgba(17,24,39,0.5);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 6px 14px;
    transition: all 0.2s ease;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background: rgba(16,185,129,0.15);
    border-color: rgba(16,185,129,0.4);
}

/* ══ 커스텀 컴포넌트 ══ */

/* 로고 */
.fab-logo {
    text-align: center;
    padding: 16px 0 8px;
}
.fab-logo-text {
    font-size: 1.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #10b981, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
}
.fab-logo-sub {
    font-size: 0.7rem;
    color: #6b7280;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 2px;
}

/* 시스템 상태 표시기 */
.sys-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.15);
    font-size: 0.8rem;
    color: #9ca3af;
}
.sys-status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px rgba(16,185,129,0.6);
    animation: pulse 2s ease-in-out infinite;
}
.sys-status-off .sys-status-dot {
    background: #ef4444;
    box-shadow: 0 0 8px rgba(239,68,68,0.6);
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
}

/* 네비게이션 */
.nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 10px;
    color: #9ca3af;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: 2px;
}
.nav-item:hover { background: rgba(255,255,255,0.04); color: #e5e7eb; }
.nav-item.active {
    background: rgba(16,185,129,0.1);
    color: #10b981;
    border-left: 3px solid #10b981;
}

/* KPI 카드 */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.kpi-card {
    background: rgba(17,24,39,0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 24px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}
.kpi-card:hover { border-color: rgba(255,255,255,0.12); transform: translateY(-2px); }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
}
.kpi-danger::before { background: linear-gradient(90deg, #ef4444, #dc2626); }
.kpi-warning::before { background: linear-gradient(90deg, #f59e0b, #d97706); }
.kpi-info::before { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.kpi-success::before { background: linear-gradient(90deg, #10b981, #059669); }

.kpi-icon {
    width: 44px; height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    margin-bottom: 16px;
}
.kpi-danger .kpi-icon { background: rgba(239,68,68,0.12); }
.kpi-warning .kpi-icon { background: rgba(245,158,11,0.12); }
.kpi-info .kpi-icon { background: rgba(59,130,246,0.12); }
.kpi-success .kpi-icon { background: rgba(16,185,129,0.12); }

.kpi-value {
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 6px;
}
.kpi-danger .kpi-value { color: #ef4444; text-shadow: 0 0 30px rgba(239,68,68,0.3); }
.kpi-warning .kpi-value { color: #f59e0b; text-shadow: 0 0 30px rgba(245,158,11,0.3); }
.kpi-info .kpi-value { color: #3b82f6; text-shadow: 0 0 30px rgba(59,130,246,0.3); }
.kpi-success .kpi-value { color: #10b981; text-shadow: 0 0 30px rgba(16,185,129,0.3); }

.kpi-label {
    color: #6b7280;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* 섹션 헤더 */
.sh {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 24px 0 16px;
}
.sh-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    background: rgba(16,185,129,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}
.sh-text {
    font-size: 1rem;
    font-weight: 700;
    color: #e5e7eb;
    letter-spacing: -0.3px;
}
.sh-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(255,255,255,0.08), transparent);
}

/* 글래스 카드 */
.glass {
    background: rgba(17,24,39,0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 24px;
}
.glass-sm {
    background: rgba(17,24,39,0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 16px;
}

/* 사이클 카드 */
.cycle-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.cycle-item {
    background: rgba(17,24,39,0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    transition: all 0.2s ease;
}
.cycle-item:hover { border-color: rgba(255,255,255,0.12); }
.cycle-val {
    font-size: 1.8rem;
    font-weight: 800;
    color: #10b981;
    line-height: 1;
    margin-bottom: 6px;
}
.cycle-lbl {
    color: #6b7280;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* 상태 뱃지 */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.badge-critical { background: rgba(239,68,68,0.12); color: #fca5a5; border: 1px solid rgba(239,68,68,0.25); }
.badge-warning { background: rgba(245,158,11,0.12); color: #fcd34d; border: 1px solid rgba(245,158,11,0.25); }
.badge-detected { background: rgba(239,68,68,0.12); color: #fca5a5; border: 1px solid rgba(239,68,68,0.2); }
.badge-in_progress { background: rgba(59,130,246,0.12); color: #93c5fd; border: 1px solid rgba(59,130,246,0.2); }
.badge-resolved { background: rgba(16,185,129,0.12); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.2); }
.badge-done { background: rgba(16,185,129,0.12); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.2); }
.badge-pending { background: rgba(107,114,128,0.12); color: #9ca3af; border: 1px solid rgba(107,114,128,0.2); }
.badge-processing { background: rgba(59,130,246,0.12); color: #93c5fd; border: 1px solid rgba(59,130,246,0.2); }
.badge-failed { background: rgba(239,68,68,0.12); color: #fca5a5; border: 1px solid rgba(239,68,68,0.2); }
.badge-info { background: rgba(59,130,246,0.12); color: #93c5fd; border: 1px solid rgba(59,130,246,0.2); }

/* 상세 카드 */
.detail-card {
    background: rgba(17,24,39,0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 12px;
}
.detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.detail-row:last-child { border-bottom: none; }
.detail-label {
    color: #6b7280;
    font-size: 0.82rem;
    font-weight: 500;
}
.detail-value {
    color: #e5e7eb;
    font-weight: 600;
    font-size: 0.9rem;
}

/* 선택 안내 */
.select-hint {
    text-align: center;
    color: #4b5563;
    padding: 60px 20px;
    font-size: 0.9rem;
}
.select-hint-icon {
    font-size: 2.5rem;
    margin-bottom: 12px;
    opacity: 0.3;
}

/* 타임라인 아이템 */
.tl-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.tl-item:last-child { border-bottom: none; }
.tl-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    margin-top: 5px;
    flex-shrink: 0;
}
.tl-dot-critical { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.5); }
.tl-dot-warning { background: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.5); }
.tl-title { color: #e5e7eb; font-size: 0.85rem; font-weight: 500; }
.tl-meta { color: #6b7280; font-size: 0.75rem; margin-top: 2px; }

/* 빈 상태 */
.empty-state {
    text-align: center;
    padding: 40px;
    color: #4b5563;
}
.empty-state-icon { font-size: 3rem; margin-bottom: 12px; opacity: 0.3; }
.empty-state-text { font-size: 0.9rem; }

/* 애니메이션 */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeInUp 0.4s ease-out; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# 헬퍼 함수
# ══════════════════════════════════════════

def badge(text: str, variant: str = "") -> str:
    cls = f"badge badge-{variant}" if variant else "badge"
    return f'<span class="{cls}">{text}</span>'


def section_header(icon: str, text: str):
    st.markdown(
        f'<div class="sh"><div class="sh-icon">{icon}</div>'
        f'<span class="sh-text">{text}</span><div class="sh-line"></div></div>',
        unsafe_allow_html=True,
    )


def detail_row(label: str, value) -> str:
    return (
        f'<div class="detail-row">'
        f'<span class="detail-label">{label}</span>'
        f'<span class="detail-value">{value}</span></div>'
    )


def kpi_card(icon: str, value, label: str, variant: str) -> str:
    return (
        f'<div class="kpi-card kpi-{variant} animate-in">'
        f'<div class="kpi-icon">{icon}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-label">{label}</div></div>'
    )


def cycle_card(value, label: str) -> str:
    return (
        f'<div class="cycle-item">'
        f'<div class="cycle-val">{value}</div>'
        f'<div class="cycle-lbl">{label}</div></div>'
    )


# ── 포맷 헬퍼 ──

_SEV_MAP = {"critical": "🔴 위험", "warning": "🟡 경고"}
_STATUS_MAP = {"detected": "🔴 감지됨", "in_progress": "🔧 처리중", "resolved": "✅ 해결"}
_CHECK_MAP = {"threshold": "📊 임계치", "delta": "📈 변화율", "absence": "🚫 부재", "llm": "🤖 AI"}
_CAT_MAP = {"logistics": "🚚 물류", "wip": "📦 재공", "equipment": "⚙️ 설비"}


def _fmt_time(t: str | None) -> str:
    if not t:
        return ""
    s = str(t)[:19]
    try:
        return s[5:10].replace("-", "/") + " " + s[11:16]
    except Exception:
        return s


# ── 차트 공통 레이아웃 ──

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#9ca3af"),
    margin=dict(l=0, r=0, t=0, b=0),
)


# ── 관리자 비밀번호 ──

try:
    ADMIN_PASSWORD = st.secrets.get("admin_password", "fab-admin")
except Exception:
    ADMIN_PASSWORD = "fab-admin"


# ── 인증 ──

if "role" not in st.session_state:
    st.session_state.role = "admin"


def _is_admin() -> bool:
    return st.session_state.get("role") == "admin"


# ══════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════

with st.sidebar:
    # 로고
    st.markdown(
        '<div class="fab-logo">'
        '<div class="fab-logo-text">FAB SENTINEL</div>'
        '<div class="fab-logo-sub">AI Anomaly Detection</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # 시스템 상태
    try:
        health = api.get_health()
        is_ok = health.get("status") == "ok"
    except Exception:
        is_ok = False

    status_cls = "sys-status" if is_ok else "sys-status sys-status-off"
    status_text = "시스템 정상" if is_ok else "연결 끊김"
    st.markdown(
        f'<div class="{status_cls}">'
        f'<div class="sys-status-dot"></div>{status_text}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # 관리자 상태
    if _is_admin():
        st.markdown(f'{badge("ADMIN", "done")}', unsafe_allow_html=True)
        if st.button("로그아웃", use_container_width=True):
            st.session_state.role = "viewer"
            st.rerun()
    else:
        with st.expander("관리자 로그인"):
            pw = st.text_input("비밀번호", type="password", key="admin_pw")
            if st.button("로그인", use_container_width=True):
                if pw == ADMIN_PASSWORD:
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("비밀번호 틀림")

    st.divider()

    page = st.radio(
        "페이지",
        ["대시보드", "이상 목록", "규칙 관리", "감지 로그"],
        label_visibility="collapsed",
    )


# ══════════════════════════════════════════
# 페이지 1: 대시보드
# ══════════════════════════════════════════

if page == "대시보드":
    st_autorefresh(interval=10_000, key="dash_refresh")

    try:
        overview = api.get_overview()
        stats = api.get_stats()
    except Exception as e:
        st.error(f"API 조회 실패: {e}")
        st.stop()

    summary = overview.get("anomaly_summary", {})
    last_cycle = overview.get("last_cycle")

    # ── KPI 카드 ──
    st.markdown(
        '<div class="kpi-grid">'
        + kpi_card("🚨", summary.get("active_critical", 0), "활성 위험", "danger")
        + kpi_card("⚠️", summary.get("active_warning", 0), "활성 경고", "warning")
        + kpi_card("📊", summary.get("total", 0), "24H 이상", "info")
        + kpi_card("📋", stats.get("active_rules", 0), "활성 규칙", "success")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1], gap="medium")

    # ── 좌: 상태 분포 (도넛) ──
    with col_left:
        section_header("📈", "상태 분포 (24h)")

        detected = summary.get("detected", 0)
        in_progress = summary.get("in_progress", 0)
        resolved = summary.get("resolved", 0)
        total = detected + in_progress + resolved

        if total > 0:
            fig = go.Figure(go.Pie(
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
            ))
            fig.update_layout(
                **_CHART_LAYOUT,
                height=260,
                showlegend=False,
                annotations=[dict(
                    text=f"<b>{total}</b><br><span style='font-size:11px;color:#6b7280'>전체</span>",
                    x=0.5, y=0.5, font=dict(size=28, color="#e5e7eb"),
                    showarrow=False,
                )],
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(
                '<div class="empty-state"><div class="empty-state-icon">✨</div>'
                '<div class="empty-state-text">감지된 이상 없음</div></div>',
                unsafe_allow_html=True,
            )

    # ── 우: 마지막 감지 사이클 ──
    with col_right:
        section_header("🔄", "마지막 감지 사이클")

        if last_cycle:
            dur = last_cycle.get("duration_ms")
            st.markdown(
                '<div class="cycle-grid">'
                + cycle_card(last_cycle.get("rules_evaluated", 0), "규칙 평가")
                + cycle_card(last_cycle.get("anomalies_found", 0), "이상 감지")
                + cycle_card(f"{dur}ms" if dur else "-", "소요시간")
                + '</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"시작: {last_cycle.get('started_at', '')}")
        else:
            st.markdown(
                '<div class="empty-state"><div class="empty-state-icon">⏳</div>'
                '<div class="empty-state-text">아직 감지 사이클이 실행되지 않았습니다</div></div>',
                unsafe_allow_html=True,
            )

        # 최근 이상 타임라인
        try:
            recent = api.get_anomalies(limit=5)
            if recent:
                section_header("⏱", "최근 이상")
                tl_html = '<div class="glass-sm">'
                for a in recent[:5]:
                    sev = a.get("severity", "warning")
                    tl_html += (
                        f'<div class="tl-item">'
                        f'<div class="tl-dot tl-dot-{sev}"></div>'
                        f'<div>'
                        f'<div class="tl-title">{(a.get("title") or "")[:40]}</div>'
                        f'<div class="tl-meta">{_fmt_time(a.get("detected_at"))} · {_CAT_MAP.get(a.get("category", ""), a.get("category", ""))}</div>'
                        f'</div></div>'
                    )
                tl_html += '</div>'
                st.markdown(tl_html, unsafe_allow_html=True)
        except Exception:
            pass

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── 수동 감지 버튼 ──
    if _is_admin():
        if st.button("⚡ 수동 감지 실행", type="primary", use_container_width=True):
            with st.spinner("감지 중..."):
                try:
                    result = api.trigger_detection()
                    st.success(
                        f"완료: {result.get('rules_evaluated', 0)}개 규칙, "
                        f"{result.get('anomalies_found', 0)}개 이상 "
                        f"({result.get('duration_ms', 0)}ms)"
                    )
                except Exception as e:
                    st.error(f"감지 실패: {e}")
    else:
        st.info("수동 감지는 관리자만 가능합니다.")


# ══════════════════════════════════════════
# 페이지 2: 이상 목록
# ══════════════════════════════════════════

elif page == "이상 목록":
    st_autorefresh(interval=10_000, key="anomaly_refresh")
    section_header("🚨", "이상 목록")

    status_filter = st.radio(
        "상태 필터",
        ["전체", "detected", "in_progress", "resolved"],
        format_func=lambda x: {
            "전체": "전체", "detected": "🔴 감지됨",
            "in_progress": "🔧 처리중", "resolved": "✅ 해결",
        }[x],
        horizontal=True,
    )

    try:
        if status_filter == "전체":
            anomalies = api.get_anomalies(limit=200)
        else:
            anomalies = api.get_anomalies(status=status_filter, limit=200)
    except Exception as e:
        st.error(f"API 조회 실패: {e}")
        st.stop()

    if not anomalies:
        st.markdown(
            '<div class="empty-state"><div class="empty-state-icon">✨</div>'
            '<div class="empty-state-text">해당 상태의 이상이 없습니다</div></div>',
            unsafe_allow_html=True,
        )
        st.stop()

    col_list, col_detail = st.columns([1, 1], gap="medium")

    with col_list:
        st.markdown(f"**{len(anomalies)}건**")
        df = pd.DataFrame([
            {
                "심각도": _SEV_MAP.get(a.get("severity", ""), a.get("severity", "")),
                "제목": (a.get("title") or "")[:45],
                "상태": _STATUS_MAP.get(a.get("status", ""), a.get("status", "")),
                "감지": _fmt_time(a.get("detected_at")),
            }
            for a in anomalies
        ])

        selection = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="anomaly_table",
            column_config={
                "심각도": st.column_config.TextColumn(width="small"),
                "제목": st.column_config.TextColumn(width="large"),
                "상태": st.column_config.TextColumn(width="small"),
                "감지": st.column_config.TextColumn(width="small"),
            },
        )

    with col_detail:
        selected_rows = selection.selection.rows if selection and selection.selection else []
        if not selected_rows:
            st.markdown(
                '<div class="detail-card"><div class="select-hint">'
                '<div class="select-hint-icon">👈</div>'
                '좌측 목록에서 이상을 선택하세요</div></div>',
                unsafe_allow_html=True,
            )
        else:
            idx = selected_rows[0]
            a = anomalies[idx]
            sev = a.get("severity", "warning")
            status_val = a.get("status", "detected")

            # 상세 카드
            sev_label = {"critical": "CRITICAL", "warning": "WARNING"}.get(sev, sev.upper())
            status_label = {"detected": "감지됨", "in_progress": "처리중", "resolved": "해결"}.get(status_val, status_val)
            badges_html = f'{badge(sev_label, sev)} {badge(status_label, status_val)}'

            detail_html = f"""
            <div class="detail-card animate-in">
                <div style="margin-bottom:16px">{badges_html}</div>
                <h3 style="color:#f3f4f6;margin:0 0 16px;font-size:1.1rem;font-weight:700;line-height:1.4">{a.get('title', '')}</h3>
                {detail_row('카테고리', _CAT_MAP.get(a.get('category', ''), a.get('category', '')))}
                {detail_row('영향 대상', a.get('affected_entity', '') or '-')}
                {detail_row('감지 시각', a.get('detected_at', '')[:19] if a.get('detected_at') else '-')}
                {detail_row('측정값', a.get('measured_value', 'N/A'))}
                {detail_row('임계치', a.get('threshold_value', 'N/A'))}
            </div>
            """
            st.markdown(detail_html, unsafe_allow_html=True)

            desc = a.get("description", "")
            if desc:
                st.markdown(f"**설명**: {desc}")

            analysis = a.get("llm_analysis")
            if analysis:
                section_header("🤖", "AI 분석")
                st.markdown(analysis)

            suggestion = a.get("llm_suggestion")
            if suggestion:
                section_header("💡", "AI 제안")
                try:
                    actions = json.loads(suggestion) if isinstance(suggestion, str) else suggestion
                    if isinstance(actions, list):
                        for i, act in enumerate(actions, 1):
                            st.markdown(f"{i}. {act}")
                    else:
                        st.markdown(str(suggestion))
                except (json.JSONDecodeError, TypeError):
                    st.markdown(str(suggestion))

            # 상태 전이
            if _is_admin():
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                current = a.get("status", "detected")
                anomaly_id = a["anomaly_id"]

                btn_cols = st.columns(2)
                if current == "detected":
                    if btn_cols[0].button("🔧 처리 시작", key=f"prog_{anomaly_id}", use_container_width=True):
                        try:
                            api.update_anomaly_status(anomaly_id, "in_progress")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                if current in ("detected", "in_progress"):
                    if btn_cols[1].button("✅ 해결", key=f"res_{anomaly_id}", use_container_width=True):
                        try:
                            api.update_anomaly_status(anomaly_id, "resolved", resolved_by="dashboard")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))


# ══════════════════════════════════════════
# 페이지 3: 규칙 관리
# ══════════════════════════════════════════

elif page == "규칙 관리":
    section_header("⚙️", "규칙 관리")

    try:
        rules = api.get_rules()
    except Exception as e:
        st.error(f"API 조회 실패: {e}")
        st.stop()

    # ── 도구 카탈로그 로드 ──
    try:
        tool_catalog = api.get_tool_catalog()
    except Exception:
        tool_catalog = {}

    def _tool_options():
        return {k: f"{v['label']} ({k})" for k, v in tool_catalog.items()}

    # ── 규칙 추가 (관리자) ──
    if _is_admin():
        with st.expander("➕ 새 규칙 추가", expanded=False):
            add_tab1, add_tab2 = st.tabs(["📐 조건 감시", "🤖 AI 판단"])

            # ── 탭1: 조건 감시 ──
            with add_tab1:
                st.markdown(
                    '<div class="glass-sm" style="margin-bottom:16px">'
                    '<p style="color:#9ca3af;margin:0;font-size:0.85rem">도구를 연결하고, 감시 조건을 설정합니다.</p></div>',
                    unsafe_allow_html=True,
                )

                tool_opts = _tool_options()
                cond_c1, cond_c2 = st.columns([2, 1])
                with cond_c1:
                    th_tool = st.selectbox(
                        "감시 도구 *",
                        options=list(tool_opts.keys()),
                        format_func=lambda x: tool_opts.get(x, x),
                        key="th_tool",
                    )
                with cond_c2:
                    check_type_labels = {
                        "threshold": "임계치 초과",
                        "delta": "변화율 초과",
                        "absence": "데이터 부재",
                    }
                    th_check_type = st.selectbox(
                        "감시 유형 *",
                        options=list(check_type_labels.keys()),
                        format_func=lambda x: check_type_labels[x],
                        key="th_check_type",
                    )

                tool_info = tool_catalog.get(th_tool, {})
                if tool_info:
                    st.caption(f"📋 {tool_info.get('description', '')}")

                if th_check_type == "delta":
                    st.info("선택한 컬럼의 **변화율(절대값)**이 임계치를 초과하면 이상으로 판단합니다.")
                elif th_check_type == "absence":
                    st.info("도구 실행 결과 **데이터가 없으면** 이상으로 판단합니다. (컬럼/임계치 불필요)")

                with st.form("threshold_form"):
                    th_name = st.text_input("규칙명 *", placeholder="예: 컨베이어 부하율 과부하")

                    if th_check_type != "absence":
                        th_column = None
                        if tool_info:
                            columns = tool_info.get("columns", [])
                            col_options = [c["name"] for c in columns]
                            col_labels = {c["name"]: c["label"] for c in columns}
                            th_column = st.selectbox(
                                "감시 컬럼 *",
                                options=col_options,
                                format_func=lambda x: f"{col_labels.get(x, x)} ({x})",
                                key="th_col",
                            )

                        tc1, tc2, tc3 = st.columns(3)
                        th_op = tc1.selectbox("조건", [">", "<", ">=", "<="], key="th_op")
                        th_warn = tc2.number_input(
                            "경고 임계치 *" if th_check_type == "threshold" else "경고 변화율(%) *",
                            value=0.0, format="%.2f", key="th_warn",
                        )
                        th_crit = tc3.number_input(
                            "위험 임계치 *" if th_check_type == "threshold" else "위험 변화율(%) *",
                            value=0.0, format="%.2f", key="th_crit",
                        )
                    else:
                        th_column = None
                        th_op = ">"
                        th_warn = 0.0
                        th_crit = 0.0

                    th_submit = st.form_submit_button("✅ 규칙 등록", type="primary")
                    if th_submit:
                        if not th_name or not th_tool:
                            st.error("규칙명과 도구는 필수입니다.")
                        else:
                            data = {
                                "rule_name": th_name,
                                "category": tool_info.get("category", "logistics"),
                                "subcategory": th_tool.replace("get_", ""),
                                "source_type": "tool",
                                "tool_name": th_tool,
                                "tool_column": th_column,
                                "check_type": th_check_type,
                                "threshold_op": th_op,
                                "warning_value": th_warn,
                                "critical_value": th_crit,
                                "eval_interval": 300,
                                "llm_enabled": 0,
                                "enabled": 1,
                            }
                            try:
                                result = api.create_rule(data)
                                st.success(f"규칙 등록 완료! (ID: {result.get('rule_id', '?')})")
                                st.rerun()
                            except Exception as e:
                                st.error(f"등록 실패: {e}")

            # ── 탭2: AI 판단 ──
            with add_tab2:
                st.markdown(
                    '<div class="glass-sm" style="margin-bottom:16px">'
                    '<p style="color:#9ca3af;margin:0;font-size:0.85rem">도구를 연결하고, 자연어로 이상 조건을 설명하면 AI가 판단합니다.</p></div>',
                    unsafe_allow_html=True,
                )

                st.markdown("**💡 이렇게 설명해보세요:**")
                st.caption("- _특정 공정만 유독 WIP가 높으면 이상. 전체적으로 높은 건 정상._")
                st.caption("- _ERROR 상태 AGV가 전체의 30%를 넘으면 위험_")
                st.caption("- _설비가 DOWN인데 알람이 없으면 비정상. 알람이 있으면 대응 중._")

                ai_tool = st.selectbox(
                    "데이터 도구 *",
                    options=list(tool_opts.keys()),
                    format_func=lambda x: tool_opts.get(x, x),
                    key="ai_tool",
                )

                ai_tool_info = tool_catalog.get(ai_tool, {})
                if ai_tool_info:
                    st.caption(f"📋 {ai_tool_info.get('description', '')}")

                with st.form("llm_form"):
                    ai_name = st.text_input("규칙명 *", placeholder="예: 특정 공정만 WIP 높으면 이상")
                    ai_prompt = st.text_area(
                        "이상 조건 설명 *",
                        height=120,
                        placeholder="이 데이터를 보고 이상인지 판단해줘. 예: 특정 공정만 유독 높으면 이상, 전체적으로 높은 건 정상.",
                        key="ai_prompt",
                    )

                    ai_submit = st.form_submit_button("✅ 규칙 등록", type="primary")
                    if ai_submit:
                        if not ai_name or not ai_tool or not ai_prompt:
                            st.error("규칙명, 도구, 이상 조건은 필수입니다.")
                        else:
                            data = {
                                "rule_name": ai_name,
                                "category": ai_tool_info.get("category", "logistics"),
                                "subcategory": ai_tool.replace("get_", ""),
                                "source_type": "tool",
                                "tool_name": ai_tool,
                                "check_type": "llm",
                                "llm_enabled": 1,
                                "llm_prompt": ai_prompt,
                                "eval_interval": 300,
                                "enabled": 1,
                            }
                            try:
                                result = api.create_rule(data)
                                st.success(f"규칙 등록 완료! (ID: {result.get('rule_id', '?')})")
                                st.rerun()
                            except Exception as e:
                                st.error(f"등록 실패: {e}")

    # ── 규칙 목록 + 상세 ──

    if not rules:
        st.markdown(
            '<div class="empty-state"><div class="empty-state-icon">📋</div>'
            '<div class="empty-state-text">등록된 규칙이 없습니다</div></div>',
            unsafe_allow_html=True,
        )
        st.stop()

    col_list, col_detail = st.columns([1, 1], gap="medium")

    with col_list:
        st.markdown(f"**{len(rules)}개 규칙**")
        df = pd.DataFrame([
            {
                "규칙명": (r.get("rule_name") or "")[:35],
                "카테고리": _CAT_MAP.get(r.get("category", ""), r.get("category", "")),
                "유형": _CHECK_MAP.get(r.get("check_type", ""), r.get("check_type", "")),
                "AI": "🟢" if r.get("llm_enabled") else "⚪",
            }
            for r in rules
        ])

        selection = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="rule_table",
            column_config={
                "규칙명": st.column_config.TextColumn(width="large"),
                "카테고리": st.column_config.TextColumn(width="small"),
                "유형": st.column_config.TextColumn(width="small"),
                "AI": st.column_config.TextColumn(width="small"),
            },
        )

    with col_detail:
        selected_rows = selection.selection.rows if selection and selection.selection else []
        if not selected_rows:
            st.markdown(
                '<div class="detail-card"><div class="select-hint">'
                '<div class="select-hint-icon">👈</div>'
                '좌측 목록에서 규칙을 선택하세요</div></div>',
                unsafe_allow_html=True,
            )
        else:
            idx = selected_rows[0]
            r = rules[idx]
            rule_id = r["rule_id"]

            is_tool = r.get("source_type") == "tool"
            src_label = "TOOL" if is_tool else "SQL"
            tool_label = ""
            if is_tool and r.get("tool_name") in tool_catalog:
                tool_label = tool_catalog[r["tool_name"]]["label"]

            ct = r.get("check_type", "threshold")
            badges_html = (
                f'{badge(_CAT_MAP.get(r.get("category", ""), r.get("category", "")), "info")} '
                f'{badge(_CHECK_MAP.get(ct, ct), "pending")} '
                f'{badge(src_label, "done" if is_tool else "processing")}'
            )

            detail_html = f"""
            <div class="detail-card animate-in">
                <div style="margin-bottom:16px">{badges_html}</div>
                <h3 style="color:#f3f4f6;margin:0 0 16px;font-size:1.1rem;font-weight:700">{r.get('rule_name', '')}</h3>
                {detail_row('데이터 소스', f'🔧 {tool_label} ({r.get("tool_name", "")})' if is_tool else '📝 SQL 쿼리')}
                {detail_row('감시 컬럼', r.get('tool_column') or '-') if is_tool else ''}
                {detail_row('연산자', r.get('threshold_op', '>')) if ct != 'llm' else ''}
                {detail_row('경고 임계치', r.get('warning_value', '-')) if ct != 'llm' else ''}
                {detail_row('위험 임계치', r.get('critical_value', '-')) if ct != 'llm' else ''}
                {detail_row('LLM 판단', '🟢 활성화' if r.get('llm_enabled') else '⚪ 비활성화')}
            </div>
            """
            st.markdown(detail_html, unsafe_allow_html=True)

            if r.get("llm_prompt"):
                st.markdown(f"**AI 조건**: {r['llm_prompt']}")

            if not is_tool and r.get("query_template"):
                st.code(r["query_template"], language="sql")

            if _is_admin():
                bc1, bc2 = st.columns(2)
                if bc1.button("🧪 테스트", key=f"test_{rule_id}", use_container_width=True):
                    with st.spinner("테스트 중..."):
                        try:
                            result = api.test_rule(rule_id)
                            st.json(result)
                        except Exception as e:
                            st.error(f"테스트 실패: {e}")
                if bc2.button("🗑 삭제", key=f"del_{rule_id}", use_container_width=True):
                    try:
                        api.delete_rule(rule_id)
                        st.success("삭제 완료")
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {e}")


# ══════════════════════════════════════════
# 페이지 4: 감지 로그
# ══════════════════════════════════════════

elif page == "감지 로그":
    st_autorefresh(interval=10_000, key="log_refresh")
    section_header("📋", "감지 로그")

    try:
        overview = api.get_overview()
        last_cycle = overview.get("last_cycle")

        if last_cycle:
            section_header("🔄", "마지막 감지 사이클")
            dur = last_cycle.get("duration_ms")
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(cycle_card(last_cycle.get("rules_evaluated", 0), "규칙 평가"), unsafe_allow_html=True)
            c2.markdown(cycle_card(last_cycle.get("anomalies_found", 0), "이상 감지"), unsafe_allow_html=True)
            c3.markdown(cycle_card(f"{dur}ms" if dur else "-", "소요시간"), unsafe_allow_html=True)
            c4.markdown(cycle_card(_fmt_time(last_cycle.get("started_at")), "시작시각"), unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="empty-state"><div class="empty-state-icon">⏳</div>'
                '<div class="empty-state-text">감지 사이클 이력이 없습니다</div></div>',
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.error(f"조회 실패: {e}")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # 최근 감지 이력
    section_header("📊", "최근 감지 이력")
    try:
        anomalies = api.get_anomalies(limit=50)
        if anomalies:
            status_labels = {"detected": "감지됨", "in_progress": "처리중", "resolved": "해결"}
            status_icons = {"detected": "🔴", "in_progress": "🔧", "resolved": "✅"}

            for status_val in ["detected", "in_progress", "resolved"]:
                filtered = [a for a in anomalies if a.get("status") == status_val]
                if filtered:
                    st.markdown(
                        f'{status_icons.get(status_val, "")} '
                        f'**{status_labels.get(status_val, status_val)}** ({len(filtered)}건)'
                    )
                    df = pd.DataFrame([
                        {
                            "심각도": _SEV_MAP.get(a.get("severity", ""), a.get("severity", "")),
                            "제목": (a.get("title") or "")[:50],
                            "카테고리": _CAT_MAP.get(a.get("category", ""), a.get("category", "")),
                            "감지": _fmt_time(a.get("detected_at")),
                        }
                        for a in filtered
                    ])
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "심각도": st.column_config.TextColumn(width="small"),
                            "제목": st.column_config.TextColumn(width="large"),
                            "카테고리": st.column_config.TextColumn(width="small"),
                            "감지": st.column_config.TextColumn(width="small"),
                        },
                    )
                    st.markdown("")
        else:
            st.markdown(
                '<div class="empty-state"><div class="empty-state-icon">✨</div>'
                '<div class="empty-state-text">감지된 이상이 없습니다</div></div>',
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.error(f"조회 실패: {e}")
