"""FAB SENTINEL — 사용자 관리 페이지."""

from __future__ import annotations

from nicegui import ui

from .. import api_client as api
from ..components import detail_row, empty_state, fmt_time, section_header
from ..theme import COLORS, ROLE_MAP

_selected_id: dict[str, int | None] = {"value": None}


@ui.refreshable
async def user_detail():
    user_id = _selected_id["value"]
    if user_id is None:
        empty_state("👈", "좌측 목록에서 사용자를 선택하세요")
        return

    try:
        users = await api.get_users()
        u = next((x for x in users if x.get("user_id") == user_id), None)
    except Exception:
        u = None

    if not u:
        empty_state("❌", "사용자 정보를 찾을 수 없습니다")
        return

    role = u.get("role", "viewer")
    role_color = COLORS["success"] if role == "admin" else COLORS["info"] if role == "operator" else COLORS["muted"]

    with ui.card().classes("glass-card animate-in p-5 w-full"):
        with ui.row().classes("gap-2 mb-4"):
            ui.badge(ROLE_MAP.get(role, role), color=role_color).props("outline").classes("text-xs font-bold")
            if u.get("enabled"):
                ui.badge("활성", color=COLORS["success"]).props("outline").classes("text-xs font-bold")
            else:
                ui.badge("비활성", color=COLORS["danger"]).props("outline").classes("text-xs font-bold")

        ui.label(u.get("display_name", u.get("username", ""))).classes("text-lg font-bold mb-4").style(
            f"color: {COLORS['text']}"
        )

        detail_row("아이디", u.get("username", ""))
        detail_row("역할", ROLE_MAP.get(role, role))
        detail_row("생성일", fmt_time(u.get("created_at")))

    # 수정 폼
    with ui.card().classes("glass-card p-5 w-full mt-4"):
        section_header("✏️", "사용자 수정")

        edit_name = ui.input(label="표시 이름", value=u.get("display_name", "")).classes("w-full mb-2")
        edit_role = ui.select(
            label="역할",
            options={"admin": "관리자", "operator": "운영자", "viewer": "열람자"},
            value=role,
        ).classes("w-full mb-2")
        edit_pw = ui.input(label="새 비밀번호 (변경 시에만 입력)", password=True).classes("w-full mb-2")
        edit_enabled = ui.switch("계정 활성화", value=bool(u.get("enabled", 1)))

        async def on_save():
            data = {}
            if edit_name.value != u.get("display_name", ""):
                data["display_name"] = edit_name.value
            if edit_role.value != role:
                data["role"] = edit_role.value
            if edit_pw.value:
                data["password"] = edit_pw.value
            if edit_enabled.value != bool(u.get("enabled", 1)):
                data["enabled"] = 1 if edit_enabled.value else 0
            if not data:
                ui.notify("변경사항이 없습니다.", type="info")
                return
            try:
                await api.update_user(user_id, data)
                ui.notify("수정 완료", type="positive")
                user_list.refresh()
                user_detail.refresh()
            except Exception as e:
                ui.notify(f"수정 실패: {e}", type="negative")

        async def on_delete():
            try:
                await api.delete_user(user_id)
                ui.notify("삭제 완료", type="positive")
                _selected_id["value"] = None
                user_list.refresh()
                user_detail.refresh()
            except Exception as e:
                ui.notify(f"삭제 실패: {e}", type="negative")

        with ui.row().classes("w-full gap-3 mt-2"):
            ui.button("💾 저장", on_click=on_save, color="primary").classes("flex-1")
            ui.button("🗑 삭제", on_click=on_delete, color="red").classes("flex-1")


@ui.refreshable
async def user_list():
    section_header("👥", "사용자 관리")

    # 사용자 추가 폼
    with ui.expansion("➕ 새 사용자 추가").classes("w-full mb-4"):
        new_username = ui.input(label="아이디 *").classes("w-full mb-2")
        new_password = ui.input(label="비밀번호 *", password=True).classes("w-full mb-2")
        new_display = ui.input(label="표시 이름").classes("w-full mb-2")
        new_role = ui.select(
            label="역할",
            options={"admin": "관리자", "operator": "운영자", "viewer": "열람자"},
            value="viewer",
        ).classes("w-full mb-2")

        async def on_create():
            if not new_username.value or not new_password.value:
                ui.notify("아이디와 비밀번호는 필수입니다.", type="warning")
                return
            try:
                result = await api.create_user({
                    "username": new_username.value,
                    "password": new_password.value,
                    "display_name": new_display.value or new_username.value,
                    "role": new_role.value,
                })
                ui.notify(f"사용자 생성 완료 (ID: {result.get('user_id', '?')})", type="positive")
                new_username.value = ""
                new_password.value = ""
                new_display.value = ""
                user_list.refresh()
            except Exception as e:
                ui.notify(f"생성 실패: {e}", type="negative")

        ui.button("✅ 사용자 등록", on_click=on_create, color="primary").classes("w-full")

    # 사용자 목록
    try:
        users_data = await api.get_users()
    except Exception as e:
        ui.notify(f"API 조회 실패: {e}", type="negative")
        return

    if not users_data:
        empty_state("👤", "등록된 사용자가 없습니다")
        return

    ui.label(f"{len(users_data)}명").classes("text-sm font-bold mb-2").style(f"color: {COLORS['muted']}")

    columns = [
        {"name": "display_name", "label": "이름", "field": "display_name", "align": "left", "sortable": True},
        {"name": "username", "label": "아이디", "field": "username", "align": "left", "sortable": True},
        {"name": "role", "label": "역할", "field": "role", "align": "left", "sortable": True},
        {"name": "enabled", "label": "상태", "field": "enabled", "align": "center", "sortable": True},
        {"name": "created_at", "label": "생성일", "field": "created_at", "align": "left", "sortable": True},
    ]
    rows = [
        {
            "id": u.get("user_id"),
            "display_name": u.get("display_name", u.get("username", "")),
            "username": u.get("username", ""),
            "role": ROLE_MAP.get(u.get("role", ""), u.get("role", "")),
            "enabled": "활성" if u.get("enabled") else "비활성",
            "created_at": fmt_time(u.get("created_at")),
        }
        for u in users_data
    ]

    search = ui.input(placeholder="검색...").props("dense outlined").classes("w-full mb-2")
    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
    table.props("flat bordered dense")
    search.bind_value_to(table, "filter")

    def on_row_click(e):
        row = e.args[1]
        _selected_id["value"] = row.get("id")
        user_detail.refresh()

    table.on("row-click", on_row_click)


async def render():
    with ui.row().classes("w-full gap-6"):
        with ui.column().classes("flex-1"):
            await user_list()
        with ui.column().classes("flex-1"):
            await user_detail()
