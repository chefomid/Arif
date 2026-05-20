"""Global keyboard shortcuts (mirrors useGlobalKeyboard.ts)."""
from __future__ import annotations

from nicegui import ui

from app.ui import handlers
from app.ui.state import View, state

_ptt_active = False


def _typing_target() -> bool:
    """Skip global shortcuts when user is typing in an input."""
    # NiceGUI doesn't expose focus easily; we track via a flag on chat input focus
    return getattr(state, "_input_focused", False)


def _can_use_global() -> bool:
    return state.view not in ("devices", "help") and not _typing_target()


async def _ptt_start() -> None:
    global _ptt_active
    if _ptt_active or not _can_use_global():
        return
    _ptt_active = True
    state.mic_hot = True
    state.notify()
    await handlers.handle_ptt_start()


async def _ptt_end() -> None:
    global _ptt_active
    if not _ptt_active:
        return
    _ptt_active = False
    state.mic_hot = False
    state.notify()
    await handlers.handle_ptt_end()


def register_keyboard(chat_input_focus_fn) -> None:
    """Register global keyboard handler and wire chat input focus tracking."""

    def set_focused(v: bool) -> None:
        state._input_focused = v  # type: ignore[attr-defined]

    chat_input_focus_fn(set_focused)

    def on_key(e) -> None:
        key = e.key
        action = getattr(e, "action", None)
        if action == "keydown":
            if key == " " and _can_use_global():
                ui.run(_ptt_start())
                return
            if not _can_use_global():
                if state.view == "devices":
                    return
                if state.view == "help" and key in ("Escape", "?"):
                    state.go_to_chat()
                return

            if key == "Escape" and state.view != "chat":
                state.go_to_chat()
            elif key == "?":
                state.open_help()
            elif key in ("d", "D"):
                state.open_devices()
            elif key in ("c", "C"):
                state.toggle_camera()
            elif key == "/":
                ui.run(focus_chat_input)

        elif action == "keyup" and key == " ":
            ui.run(_ptt_end())

    ui.keyboard(on_key=on_key, ignore=['input', 'textarea'])


def focus_chat_input() -> None:
    ui.run_javascript(
        'const el = document.getElementById("chat-input"); if (el) { el.focus(); }',
        timeout=1.0,
    )
