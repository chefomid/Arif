"""Main NiceGUI page — mirrors React AppShell + panels."""
from __future__ import annotations

import asyncio
from pathlib import Path

from nicegui import ui

from app.services.device_manager import device_manager
from app.services.llm_client import llm_client
from app.ui import handlers
from app.ui.keyboard import focus_chat_input
from app.ui.state import state

_THEME = Path(__file__).parent / "theme.css"
_prev_view: list[str] = ["chat"]
_chat_input: ui.textarea | None = None
_refresh_main: list = []


def _load_devices() -> None:
    state.devices_loading = True
    state.notify()
    try:
        state.apply_device_status(device_manager.status())
        state.devices_error = ""
    except Exception as exc:
        state.devices_error = str(exc)
    finally:
        state.devices_loading = False
        state.notify()


async def _check_llm() -> None:
    try:
        state.llm_healthy = await llm_client.health_check()
    except Exception:
        state.llm_healthy = False
    state.notify()


async def _on_view_changed() -> None:
    prev = _prev_view[0]
    if state.view == "camera" and prev != "camera":
        await handlers.handle_camera_subscribe_ui()
        from app.services.yolo import yolo_service

        yolo_service.start()
    elif prev == "camera" and state.view != "camera":
        await handlers.handle_camera_unsubscribe_ui()
    if state.view == "devices":
        _load_devices()
    _prev_view[0] = state.view


def _device_rows() -> list:
    rows: list = [{"kind": "mic-default"}]
    rows.extend({"kind": "mic", "index": d.index} for d in state.audio_devices)
    rows.extend({"kind": "cam", "index": d.index} for d in state.camera_devices)
    return rows


def _row_label(row: dict) -> str:
    if row["kind"] == "mic-default":
        return "[System default microphone]"
    if row["kind"] == "mic":
        d = next((x for x in state.audio_devices if x.index == row["index"]), None)
        return f"Mic: {d.name}" if d else f"Mic {row['index']}"
    d = next((x for x in state.camera_devices if x.index == row["index"]), None)
    return f"Cam: {d.name}" if d else f"Camera {row['index']}"


def _row_selected(row: dict) -> bool:
    if row["kind"] == "mic-default":
        return not any(d.selected for d in state.audio_devices)
    if row["kind"] == "mic":
        d = next((x for x in state.audio_devices if x.index == row["index"]), None)
        return bool(d and d.selected)
    d = next((x for x in state.camera_devices if x.index == row["index"]), None)
    return bool(d and d.selected)


async def _select_device_row(row: dict) -> None:
    try:
        if row["kind"] == "mic-default":
            device_manager.set_mic(None)
        elif row["kind"] == "mic":
            device_manager.set_mic(row["index"])
        elif row["kind"] == "cam":
            device_manager.set_camera(row["index"])
        state.apply_device_status(device_manager.status())
    except Exception as exc:
        state.devices_error = str(exc)
        state.notify()


def _build_overlay_svg() -> str:
    if state.frame_width <= 0:
        return ""
    parts = [
        f'<svg class="arif-detection-overlay" viewBox="0 0 {state.frame_width} {state.frame_height}" '
        'preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%;">'
    ]
    for d in state.detections:
        x = d.x * state.frame_width
        y = d.y * state.frame_height
        w = d.w * state.frame_width
        h = d.h * state.frame_height
        label = f"{d.class_name} {d.confidence * 100:.0f}%"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="arif-bbox"/>'
            f'<text x="{x}" y="{max(y - 4, 10)}" class="arif-bbox-label">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


@ui.refreshable
def _render_messages() -> None:
    if state.view != "chat":
        return
    with ui.column().classes("arif-messages w-full"):
        if not state.messages and not state.partial_transcript:
            ui.label("Ready. Type below or hold Space to speak.").classes("arif-msg-system")
        for m in state.messages:
            cls = {
                "system": "arif-msg-system",
                "user": "arif-msg-user",
                "assistant": "arif-msg-assistant",
            }.get(m.role, "arif-msg-user")
            ui.label(m.content).classes(cls)
        if state.partial_transcript:
            rec = " recording" if state.mic_hot else ""
            ui.label(state.partial_transcript).classes(f"arif-msg-partial{rec}")


@ui.refreshable
def _render_chat_panel() -> None:
    if state.view != "chat":
        return
    with ui.column().classes("arif-chat-panel w-full h-full"):
        ui.label("# Press ? for keys · D devices · C camera · / to type").classes(
            "arif-terminal-banner"
        )
        _render_messages()
        with ui.row().classes("arif-input-row w-full"):
            global _chat_input
            _chat_input = (
                ui.textarea(value="", placeholder="Enter command or message…")
                .props('id=chat-input rows=2 outlined dense')
                .classes("flex-grow arif-chat-input")
            )
            _chat_input.on(
                "focus",
                lambda: setattr(state, "_input_focused", True),  # type: ignore[attr-defined]
            )
            _chat_input.on(
                "blur",
                lambda: setattr(state, "_input_focused", False),  # type: ignore[attr-defined]
            )

            def send() -> None:
                text = (_chat_input.value or "").strip() if _chat_input else ""
                if not text or state.is_streaming:
                    return
                state.add_message("user", text)
                if _chat_input:
                    _chat_input.value = ""
                ui.run(handlers.handle_chat_send_ui(text))

            def on_enter(e) -> None:
                if e.args.get("key") == "Enter" and not e.args.get("shiftKey"):
                    send()

            _chat_input.on("keydown", on_enter)

            send_btn = ui.button("Send", on_click=send).classes("arif-send-btn")
            send_btn.bind_enabled_from(state, "is_streaming", backward=lambda s: not s)


@ui.refreshable
def _render_camera_panel() -> None:
    if state.view != "camera":
        return
    with ui.column().classes("arif-camera-view w-full h-full"):
        with ui.element("div").classes("arif-camera-feed-wrap w-full"):
            ui.image("/api/vision/camera/mjpeg").classes("arif-camera-feed")
            overlay = _build_overlay_svg()
            if overlay:
                ui.html(overlay).classes("w-full h-full")
        with ui.column().classes("arif-detection-list w-full"):
            ui.html("<h3>Detections</h3>")
            if not state.detections:
                ui.label("No objects detected").style("color: var(--ps-dim)")
            else:
                with ui.row().classes("flex-wrap"):
                    for d in state.detections:
                        ui.label(
                            f"{d.class_name} {d.confidence * 100:.0f}%"
                        ).classes("arif-det-tag")


@ui.refreshable
def _render_devices_panel() -> None:
    if state.view != "devices":
        return
    rows = _device_rows()
    state.device_cursor = min(state.device_cursor, max(0, len(rows) - 1))

    with ui.column().classes("arif-device-panel w-full h-full"):
        with ui.row().classes("w-full items-baseline gap-4"):
            ui.label("# Devices").classes("arif-device-header")
            ui.label("↑↓ move · Enter select · A auto · Esc back").classes("arif-device-hint")
        ui.label(f"Mic: {state.mic_name}").style("color: var(--ps-cyan)")
        ui.label(f"Cam: {state.camera_name}").style("color: var(--ps-cyan)")
        if state.devices_loading:
            ui.label("Scanning devices…").style("color: var(--ps-dim)")
        if state.devices_error:
            ui.label(state.devices_error).style("color: var(--ps-red)")
        with ui.column().classes("w-full flex-grow overflow-auto"):
            if not rows and not state.devices_loading:
                ui.label(
                    "No devices found. Plug in USB mic/camera and press A."
                ).style("color: var(--ps-dim); font-style: italic")
            for i, row in enumerate(rows):
                focused = i == state.device_cursor
                selected = _row_selected(row)
                cls = "arif-device-row"
                if focused:
                    cls += " focused"
                if selected:
                    cls += " selected"
                label = _row_label(row)
                if selected:
                    label += " ◀ active"
                ui.label(label).classes(cls)


@ui.refreshable
def _render_help_panel() -> None:
    if state.view != "help":
        return
    shortcuts = [
        ("/", "Focus message input"),
        ("Space (hold)", "Push-to-talk / record voice"),
        ("Enter", "Send message (in input)"),
        ("C", "Toggle camera view"),
        ("D", "Open device picker"),
        ("A", "Auto-detect devices (in device picker)"),
        ("↑ / ↓", "Navigate device list"),
        ("Esc", "Back to chat / close panel"),
        ("?", "This help screen"),
    ]
    with ui.column().classes("arif-help-panel w-full h-full"):
        ui.label("# Keyboard shortcuts").classes("text-lg").style("color: var(--ps-yellow)")
        ui.label("Navigation works without mouse. Esc returns to chat.").style(
            "color: var(--ps-dim)"
        )
        for key, desc in shortcuts:
            with ui.row().classes("w-full"):
                ui.label(key).classes("arif-help-key").style("min-width: 8rem")
                ui.label(desc).classes("arif-help-desc")
        ui.label("Press Esc or ? to close").style("color: var(--ps-dim); margin-top: 1.5rem")


@ui.refreshable
def _render_toolbar() -> None:
    with ui.row().classes("arif-toolbar w-full"):
        with ui.row().classes("arif-toolbar-brand"):
            ui.label("PS").classes("arif-ps-prompt")
            ui.label("Arif://multimodal").classes("arif-title")
        with ui.row().classes("arif-toolbar-actions"):
            mic_cls = "arif-mic-hot" + (" active" if state.mic_hot else "")
            with ui.row().classes(mic_cls):
                ui.element("div").classes("arif-mic-dot")
                ui.label("MIC ON" if state.mic_hot else "MIC off").classes("arif-mic-label")

            ptt_cls = "arif-toolbar-btn arif-ptt" + (" hot" if state.mic_hot else "")

            async def ptt_down() -> None:
                from app.ui.keyboard import _ptt_start

                await _ptt_start()

            async def ptt_up() -> None:
                from app.ui.keyboard import _ptt_end

                await _ptt_end()

            btn = ui.button(
                f"{'●' if state.mic_hot else '○'} "
                f"{'[PTT ACTIVE]' if state.mic_hot else '[Hold Space]'}",
                on_mousedown=ptt_down,
                on_mouseup=ptt_up,
                on_mouseleave=ptt_up,
            ).classes(ptt_cls)

            def nav_btn(label: str, active: bool, on_click) -> None:
                cls = "arif-toolbar-btn" + (" active" if active else "")
                ui.button(label, on_click=on_click).classes(cls)

            nav_btn("[Devices]", state.view == "devices", state.open_devices)
            nav_btn(
                "[Camera]",
                state.view == "camera",
                state.toggle_camera,
            )
            nav_btn("[?]", state.view == "help", state.open_help)

        with ui.row().classes("arif-status"):
            ws_cls = "arif-dot ws on" if state.ws_connected else "arif-dot off"
            llm_cls = "arif-dot llm on" if state.llm_healthy else "arif-dot off"
            with ui.row().classes("items-center gap-1"):
                ui.element("div").classes(ws_cls)
                ui.label("link").classes("arif-status-label")
            with ui.row().classes("items-center gap-1"):
                ui.element("div").classes(llm_cls)
                ui.label("llm").classes("arif-status-label")


@ui.refreshable
def _render_device_bar() -> None:
    with ui.row().classes("arif-device-bar w-full"):
        ui.label(f"mic: {state.mic_name}").classes("arif-device-bar-item")
        ui.label("|").classes("arif-device-bar-sep")
        ui.label(f"cam: {state.camera_name}").classes("arif-device-bar-item")
        ui.label("? help · D devices · C camera · Esc back").classes("arif-device-bar-hint")


@ui.refreshable
def _render_main() -> None:
    with ui.column().classes("arif-panel w-full h-full"):
        _render_chat_panel()
        _render_camera_panel()
        _render_devices_panel()
        _render_help_panel()


def _refresh_all() -> None:
    if _prev_view[0] != state.view:
        ui.run(_on_view_changed())
    _render_toolbar.refresh()
    _render_device_bar.refresh()
    _render_main.refresh()
    _render_messages.refresh()


def _device_keyboard(e) -> bool:
    """Handle device panel keys; return True if handled."""
    if state.view != "devices":
        return False
    key = e.key
    action = getattr(e, "action", "keydown")
    if action != "keydown":
        return False
    rows = _device_rows()
    if key == "Escape":
        state.go_to_chat()
        return True
    if key in ("a", "A"):
        ui.run(_device_auto)
        return True
    if key == "ArrowDown":
        state.device_cursor = min(state.device_cursor + 1, max(0, len(rows) - 1))
        state.notify()
        return True
    if key == "ArrowUp":
        state.device_cursor = max(state.device_cursor - 1, 0)
        state.notify()
        return True
    if key == "Enter" and rows:
        row = rows[state.device_cursor]
        ui.run(lambda: _select_device_row(row))
        return True
    return False


async def _device_auto() -> None:
    try:
        state.apply_device_status(device_manager.auto_select())
    except Exception as exc:
        state.devices_error = str(exc)
        state.notify()


@ui.page("/")
def arif_page() -> None:
    ui.add_css(_THEME.read_text(encoding="utf-8"))
    state._input_focused = False  # type: ignore[attr-defined]
    state.on_refresh(_refresh_all)

    with ui.column().classes("arif-shell w-full"):
        _render_toolbar()
        _render_device_bar()
        _render_main()

    def on_key(e) -> None:
        if _device_keyboard(e):
            return
        if state.view == "help" and getattr(e, "action", "") == "keydown":
            if e.key in ("Escape", "?"):
                state.go_to_chat()
                return

        from app.ui import keyboard as kb

        key = e.key
        action = getattr(e, "action", "keydown")
        typing = getattr(state, "_input_focused", False)

        if action == "keydown" and key == " " and state.view not in ("devices", "help") and not typing:
            ui.run(kb._ptt_start)
            return
        if action == "keyup" and key == " ":
            ui.run(kb._ptt_end)
            return

        if state.view in ("devices", "help") or typing:
            return

        if action == "keydown":
            if key == "Escape" and state.view != "chat":
                state.go_to_chat()
            elif key == "?":
                state.open_help()
            elif key in ("d", "D"):
                state.open_devices()
            elif key in ("c", "C"):
                state.toggle_camera()
            elif key == "/":
                focus_chat_input()

    ui.keyboard(on_key=on_key, ignore=["input", "textarea"])

    ui.timer(10.0, lambda: ui.run(_check_llm()))
    ui.run(_check_llm())
    _load_devices()
