"""FLOPI — NiceGUI 대시보드 진입점."""

from __future__ import annotations

from nicegui import app, ui

from .theme import COLORS, ROLE_MAP, apply_theme
from . import api_client as api
from .pages import dashboard, anomalies, rules, logs, users

app.storage_secret = "fab-sentinel-secret"

NAV_ITEMS = [
    ("/", "📊", "대시보드", None),
    ("/anomalies", "🚨", "이상 목록", None),
    ("/rules", "⚙️", "규칙 관리", None),
    ("/logs", "📋", "감지 로그", None),
    ("/users", "👥", "사용자 관리", "admin"),
]


async def create_layout(active: str):
    """공유 레이아웃: 좌측 드로어 + 네비게이션."""
    is_dark = app.storage.user.get("dark_mode", True)
    ui.dark_mode(is_dark)
    apply_theme(is_dark)

    with ui.left_drawer(fixed=True).classes("p-4").style("width: 240px"):
        # 로고
        ui.html(
            '<div style="text-align:center; padding: 8px 0 16px">'
            '<div style="font-size:1.5rem; font-weight:800; '
            "background: linear-gradient(135deg, #10b981, #3b82f6); "
            '-webkit-background-clip: text; -webkit-text-fill-color: transparent">'
            "FLOPI</div>"
            '<div style="font-size:0.65rem; color:#6b7280; letter-spacing:0.15em; '
            'text-transform:uppercase; margin-top:2px">AI Anomaly Detection</div></div>'
        )

        # 시스템 상태
        @ui.refreshable
        async def system_status():
            try:
                health = await api.get_health()
                is_ok = health.get("status") == "ok"
            except Exception:
                is_ok = False
            dot_color = "#10b981" if is_ok else "#ef4444"
            text = "시스템 정상" if is_ok else "연결 끊김"
            with ui.row().classes("items-center gap-2 justify-center w-full py-2"):
                ui.element("div").classes("pulse-dot").style(f"background: {dot_color}")
                ui.label(text).classes("text-xs font-medium").style(f"color: {COLORS['muted']}")

        await system_status()
        ui.timer(30.0, system_status.refresh)

        ui.separator().classes("my-3 opacity-10")

        # 사용자 상태
        role = app.storage.user.get("role", "")
        username = app.storage.user.get("username", "")
        display_name = app.storage.user.get("display_name", "")

        if role and username:
            # 로그인된 상태
            role_label = ROLE_MAP.get(role, role.upper())
            role_color = COLORS["success"] if role == "admin" else COLORS["info"] if role == "operator" else COLORS["muted"]
            with ui.column().classes("w-full gap-1"):
                with ui.row().classes("items-center justify-between w-full"):
                    ui.badge(role_label, color=role_color).props("outline")

                    def logout():
                        app.storage.user.update({"role": "", "username": "", "display_name": ""})
                        ui.navigate.reload()

                    ui.button("로그아웃", on_click=logout, color=None).props("flat dense size=sm").classes(
                        "text-xs"
                    )
                ui.label(display_name or username).classes("text-sm font-medium").style(
                    f"color: {COLORS['text']}"
                )
        else:
            # 로그인 / 회원가입 폼 — visibility 토글
            login_col = ui.column().classes("w-full")
            register_col = ui.column().classes("w-full")

            def show_register():
                login_col.visible = False
                register_col.visible = True

            def show_login():
                register_col.visible = False
                login_col.visible = True

            with login_col:
                id_input = ui.input("아이디").props("dense outlined").classes("w-full")
                pw_input = ui.input("비밀번호", password=True).props("dense outlined").classes("w-full")

                async def do_login():
                    if not id_input.value or not pw_input.value:
                        ui.notify("아이디와 비밀번호를 입력하세요.", type="warning")
                        return
                    try:
                        result = await api.login(id_input.value, pw_input.value)
                        app.storage.user["role"] = result["role"]
                        app.storage.user["username"] = result["username"]
                        app.storage.user["display_name"] = result.get("display_name", result["username"])
                        ui.navigate.reload()
                    except Exception:
                        ui.notify("로그인 실패", type="negative")

                ui.button("로그인", on_click=do_login, color="primary").props("dense size=sm").classes("w-full")
                ui.button("회원가입", on_click=show_register, color=None).props(
                    "flat dense no-caps size=sm"
                ).classes("w-full text-xs")

            with register_col:
                reg_id = ui.input("아이디").props("dense outlined").classes("w-full")
                reg_pw = ui.input("비밀번호", password=True).props("dense outlined").classes("w-full")
                reg_name = ui.input("이름").props("dense outlined").classes("w-full")

                async def do_register():
                    if not reg_id.value or not reg_pw.value:
                        ui.notify("아이디와 비밀번호는 필수입니다.", type="warning")
                        return
                    if len(reg_pw.value) < 4:
                        ui.notify("비밀번호는 4자 이상이어야 합니다.", type="warning")
                        return
                    try:
                        result = await api.register(reg_id.value, reg_pw.value, reg_name.value)
                        app.storage.user["role"] = result["role"]
                        app.storage.user["username"] = result["username"]
                        app.storage.user["display_name"] = result.get("display_name", result["username"])
                        ui.notify(f"가입 완료!", type="positive")
                        ui.navigate.reload()
                    except Exception as e:
                        msg = str(e)
                        if "409" in msg:
                            ui.notify("이미 사용 중인 아이디입니다.", type="negative")
                        else:
                            ui.notify(f"가입 실패", type="negative")

                ui.button("회원가입", on_click=do_register, color="primary").props("dense size=sm").classes("w-full")
                ui.button("로그인으로", on_click=show_login, color=None).props(
                    "flat dense no-caps size=sm"
                ).classes("w-full text-xs")

            register_col.visible = False

        ui.separator().classes("my-3 opacity-10")

        # 네비게이션
        for path, emoji, label, required_role in NAV_ITEMS:
            if required_role and role != required_role:
                continue
            is_active = active == path
            color = COLORS["primary"] if is_active else COLORS["muted"]
            bg = "rgba(16,185,129,0.1)" if is_active else "transparent"
            ui.button(
                f"{emoji}  {label}",
                on_click=lambda p=path: ui.navigate.to(p),
                color=None,
            ).props("flat align=left no-caps").classes("w-full").style(
                f"color: {color}; background: {bg}; border-radius: 8px; justify-content: flex-start"
            )

        # 하단 여백 + 테마 토글
        ui.space()

        def toggle_theme():
            current = app.storage.user.get("dark_mode", True)
            app.storage.user["dark_mode"] = not current
            ui.navigate.reload()

        theme_emoji = "☀️" if is_dark else "🌙"
        theme_label = "라이트 모드" if is_dark else "다크 모드"
        ui.button(
            f"{theme_emoji}  {theme_label}",
            on_click=toggle_theme,
            color=None,
        ).props("flat align=left no-caps").classes("w-full").style(
            f"color: {COLORS['muted']}; border-radius: 8px; justify-content: flex-start"
        )


@ui.page("/")
async def page_dashboard():
    await create_layout("/")
    await dashboard.render()


@ui.page("/anomalies")
async def page_anomalies():
    await create_layout("/anomalies")
    await anomalies.render()


@ui.page("/rules")
async def page_rules():
    await create_layout("/rules")
    await rules.render()


@ui.page("/logs")
async def page_logs():
    await create_layout("/logs")
    await logs.render()


@ui.page("/users")
async def page_users():
    await create_layout("/users")
    role = app.storage.user.get("role", "")
    if role != "admin":
        ui.label("관리자만 접근 가능합니다.").classes("text-lg font-bold").style(f"color: {COLORS['danger']}")
        return
    await users.render()


def main():
    ui.run(
        port=3009,
        title="FLOPI",
        dark=True,
        reload=False,
        storage_secret="fab-sentinel-secret",
    )


if __name__ == "__main__":
    main()
