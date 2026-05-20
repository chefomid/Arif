"""Event bridge: PTT + vision fan-out to UI and WebSocket clients."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.schemas.messages import ServerMessage, WsMessageType
from app.services.ptt_pipeline import ptt_pipeline
from app.services.yolo import yolo_service
from app.ui import handlers
from app.ui.state import state

if TYPE_CHECKING:
    from app.ws.gateway import ConnectionManager

logger = logging.getLogger(__name__)

_vision_queue: asyncio.Queue | None = None
_main_loop: asyncio.AbstractEventLoop | None = None
_manager: ConnectionManager | None = None


def register_connection_manager(manager: ConnectionManager) -> None:
    global _manager
    _manager = manager


def register_ptt_callbacks() -> None:
    """Single PTT callback chain for UI + all WebSocket clients."""

    async def on_partial(text: str) -> None:
        state.on_stt_partial(text)
        if _manager:
            msg = ServerMessage(type=WsMessageType.STT_PARTIAL, payload={"text": text})
            await _manager.broadcast_all(msg)

    async def on_final(text: str) -> None:
        state.on_stt_final(text, auto_send=False)
        if _manager:
            msg = ServerMessage(type=WsMessageType.STT_FINAL, payload={"text": text})
            await _manager.broadcast_all(msg)

    async def on_auto_send(text: str) -> None:
        state.on_stt_final(text, auto_send=True)
        if _manager:
            msg = ServerMessage(
                type=WsMessageType.STT_FINAL,
                payload={"text": text, "auto_send": True},
            )
            await _manager.broadcast_all(msg)
        await handlers.stream_chat_to_ui(text)

    ptt_pipeline.set_callbacks(on_partial, on_final, on_auto_send)


def setup_vision_broadcast(manager: ConnectionManager) -> None:
    """Register YOLO callback; push vision_frame_meta to UI + WS subscribers."""
    global _vision_queue, _main_loop, _manager
    _manager = manager
    _vision_queue = asyncio.Queue(maxsize=64)
    _main_loop = asyncio.get_running_loop()

    async def vision_pump() -> None:
        while True:
            ts, detections, w, h = await _vision_queue.get()
            has_ws = bool(manager._vision_subscribers)
            has_ui = handlers.is_ui_vision_subscribed()
            if not has_ws and not has_ui:
                continue

            if has_ui:
                handlers.apply_vision_to_ui(ts, detections, w, h)

            if has_ws:
                msg = ServerMessage(
                    type=WsMessageType.VISION_FRAME_META,
                    payload=handlers.vision_payload(ts, detections, w, h),
                )
                await manager.broadcast_vision(msg)

    asyncio.create_task(vision_pump())

    def sync_callback(ts, detections, w, h) -> None:
        if _vision_queue is None or _main_loop is None:
            return
        try:
            _vision_queue.put_nowait((ts, detections, w, h))
        except asyncio.QueueFull:
            pass

    yolo_service.subscribe(sync_callback)
