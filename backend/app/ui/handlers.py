"""Shared handlers for WebSocket clients and in-process NiceGUI UI."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.schemas.messages import Detection, ServerMessage, WsMessageType
from app.services.chat import chat_service
from app.services.ptt_pipeline import ptt_pipeline
from app.services.yolo import yolo_service
from app.ui.state import AppState, Detection as UiDetection, state

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.ws.gateway import ConnectionManager

logger = logging.getLogger(__name__)

_ui_vision_subscribed = False


def is_ui_vision_subscribed() -> bool:
    return _ui_vision_subscribed


async def handle_ptt_start() -> None:
    await ptt_pipeline.start()


async def handle_ptt_end() -> None:
    await ptt_pipeline.end()


async def handle_camera_subscribe_ui() -> None:
    global _ui_vision_subscribed
    _ui_vision_subscribed = True
    if not yolo_service.is_running():
        yolo_service.start()


async def handle_camera_unsubscribe_ui() -> None:
    global _ui_vision_subscribed
    _ui_vision_subscribed = False


async def handle_camera_subscribe_ws(ws: WebSocket, manager: ConnectionManager) -> None:
    manager._vision_subscribers.add(ws)
    if not yolo_service.is_running():
        yolo_service.start()
    await manager.send(
        ws,
        ServerMessage(type=WsMessageType.PONG, payload={"subscribed": "camera"}),
    )


def handle_camera_unsubscribe_ws(ws: WebSocket, manager: ConnectionManager) -> None:
    manager._vision_subscribers.discard(ws)


async def stream_chat_to_ui(text: str, app_state: AppState | None = None) -> None:
    st = app_state or state
    if not text.strip():
        return
    try:
        async for token in chat_service.send_stream(text):
            st.on_chat_token(token)
        st.on_chat_done()
    except Exception as exc:
        logger.exception("Chat stream failed")
        st.add_message("system", f"Error: {exc}")
        st.on_chat_done()


async def stream_chat_to_ws(ws: WebSocket, text: str, manager: ConnectionManager) -> None:
    if not text.strip():
        return
    try:
        async for token in chat_service.send_stream(text):
            await manager.send(
                ws,
                ServerMessage(type=WsMessageType.CHAT_TOKEN, payload={"token": token}),
            )
        await manager.send(ws, ServerMessage(type=WsMessageType.CHAT_DONE, payload={}))
    except Exception as exc:
        await manager.send(
            ws,
            ServerMessage(type=WsMessageType.ERROR, payload={"message": str(exc)}),
        )


async def handle_chat_send_ui(text: str) -> None:
    await stream_chat_to_ui(text)


async def handle_chat_send_ws(ws: WebSocket, text: str, manager: ConnectionManager) -> None:
    await stream_chat_to_ws(ws, text, manager)


def vision_payload(ts: float, detections: list[Detection], w: int, h: int) -> dict:
    return {
        "ts": ts,
        "detections": [d.model_dump() for d in detections],
        "frame_width": w,
        "frame_height": h,
    }


def apply_vision_to_ui(ts: float, detections: list[Detection], w: int, h: int) -> None:
    ui_dets = [
        UiDetection(
            class_name=d.class_name,
            confidence=d.confidence,
            x=d.x,
            y=d.y,
            w=d.w,
            h=d.h,
        )
        for d in detections
    ]
    state.set_frame_meta(ui_dets, w, h, ts)
