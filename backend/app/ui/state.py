"""Application UI state (replaces React Zustand stores)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

View = Literal["chat", "camera", "devices", "help"]
MessageRole = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    id: str
    role: MessageRole
    content: str
    streaming: bool = False


@dataclass
class Detection:
    class_name: str
    confidence: float
    x: float
    y: float
    w: float
    h: float


@dataclass
class AudioDeviceRow:
    index: int
    name: str
    selected: bool = False


@dataclass
class CameraDeviceRow:
    index: int
    name: str
    width: int = 0
    height: int = 0
    selected: bool = False


class AppState:
    """Singleton UI state with optional refresh callbacks."""

    def __init__(self) -> None:
        self._msg_counter = 0
        self._streaming_msg_id: str | None = None
        self._refresh: list[Callable[[], None]] = []

        # ui store
        self.view: View = "chat"
        self.ws_connected: bool = True  # in-process UI is always "connected"
        self.llm_healthy: bool = False
        self.mic_hot: bool = False

        # chat store
        self.messages: list[ChatMessage] = []
        self.is_streaming: bool = False
        self.partial_transcript: str = ""

        # device store
        self.mic_name: str = "…"
        self.camera_name: str = "…"
        self.audio_devices: list[AudioDeviceRow] = []
        self.camera_devices: list[CameraDeviceRow] = []
        self.devices_loading: bool = False
        self.devices_error: str = ""

        # vision store
        self.detections: list[Detection] = []
        self.frame_width: int = 0
        self.frame_height: int = 0
        self.last_ts: float = 0.0

        # device panel cursor
        self.device_cursor: int = 0

        # camera view active
        self.camera_subscribed: bool = False

    def on_refresh(self, cb: Callable[[], None]) -> None:
        self._refresh.append(cb)

    def notify(self) -> None:
        for cb in self._refresh:
            try:
                cb()
            except Exception:
                pass

    def _next_msg_id(self) -> str:
        self._msg_counter += 1
        return f"msg-{self._msg_counter}"

    def add_message(self, role: MessageRole, content: str) -> str:
        mid = self._next_msg_id()
        self.messages.append(ChatMessage(id=mid, role=role, content=content))
        self.notify()
        return mid

    def append_to_message(self, msg_id: str, token: str) -> None:
        for m in self.messages:
            if m.id == msg_id:
                m.content += token
                break
        self.notify()

    def finish_streaming(self) -> None:
        self.is_streaming = False
        self._streaming_msg_id = None
        for m in self.messages:
            m.streaming = False
        self.notify()

    def set_partial_transcript(self, text: str) -> None:
        self.partial_transcript = text
        self.notify()

    def clear_partial_transcript(self) -> None:
        self.partial_transcript = ""
        self.notify()

    def set_view(self, view: View) -> None:
        self.view = view
        self.notify()

    def toggle_camera(self) -> None:
        self.view = "chat" if self.view == "camera" else "camera"
        self.notify()

    def go_to_chat(self) -> None:
        self.view = "chat"
        self.notify()

    def open_devices(self) -> None:
        self.view = "devices"
        self.device_cursor = 0
        self.notify()

    def open_help(self) -> None:
        self.view = "help"
        self.notify()

    def set_frame_meta(
        self,
        detections: list[Detection],
        frame_width: int,
        frame_height: int,
        ts: float,
    ) -> None:
        self.detections = detections
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.last_ts = ts
        self.notify()

    def apply_device_status(self, data: dict) -> None:
        mic = data.get("mic") or {}
        cam = data.get("camera") or {}
        self.mic_name = mic.get("name") or "—"
        self.camera_name = cam.get("name") or "—"
        self.audio_devices = [
            AudioDeviceRow(
                index=d["index"],
                name=d.get("name", f"Mic {d['index']}"),
                selected=bool(d.get("selected")),
            )
            for d in data.get("audio_devices", [])
        ]
        self.camera_devices = [
            CameraDeviceRow(
                index=d["index"],
                name=d.get("name", f"Camera {d['index']}"),
                width=int(d.get("width") or 0),
                height=int(d.get("height") or 0),
                selected=bool(d.get("selected")),
            )
            for d in data.get("camera_devices", [])
        ]
        self.notify()

    def on_stt_partial(self, text: str) -> None:
        self.set_partial_transcript(text)

    def on_stt_final(self, text: str, auto_send: bool = False) -> None:
        if auto_send and text:
            self.add_message("user", text)
            self.clear_partial_transcript()
        else:
            self.set_partial_transcript(text)

    def on_chat_token(self, token: str) -> None:
        if not self._streaming_msg_id:
            self._streaming_msg_id = self.add_message("assistant", "")
            self.is_streaming = True
        if self._streaming_msg_id:
            self.append_to_message(self._streaming_msg_id, token)

    def on_chat_done(self) -> None:
        self.finish_streaming()
        self.clear_partial_transcript()


state = AppState()
