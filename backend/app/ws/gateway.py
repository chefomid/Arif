import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.messages import ClientMessage, ServerMessage, WsMessageType
from app.services.chat import chat_service
from app.services.ptt_pipeline import ptt_pipeline
from app.services.yolo import yolo_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._vision_subscribers: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        self._vision_subscribers.discard(ws)

    async def send(self, ws: WebSocket, msg: ServerMessage) -> None:
        await ws.send_text(msg.model_dump_json())

    async def broadcast_vision(self, msg: ServerMessage) -> None:
        dead: list[WebSocket] = []
        for ws in self._vision_subscribers:
            try:
                await self.send(ws, msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._vision_subscribers.discard(ws)


manager = ConnectionManager()


def _parse_client(data: str) -> ClientMessage | None:
    try:
        raw = json.loads(data)
        return ClientMessage(**raw)
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_gateway(ws: WebSocket):
    await manager.connect(ws)

    async def on_partial(text: str) -> None:
        await manager.send(
            ws,
            ServerMessage(type=WsMessageType.STT_PARTIAL, payload={"text": text}),
        )

    async def on_final(text: str) -> None:
        await manager.send(
            ws,
            ServerMessage(type=WsMessageType.STT_FINAL, payload={"text": text}),
        )

    async def on_auto_send(text: str) -> None:
        await manager.send(
            ws,
            ServerMessage(type=WsMessageType.STT_FINAL, payload={"text": text, "auto_send": True}),
        )
        await _handle_chat_send(ws, text)

    ptt_pipeline.set_callbacks(on_partial, on_final, on_auto_send)

    try:
        while True:
            data = await ws.receive_text()
            msg = _parse_client(data)
            if not msg:
                await manager.send(
                    ws,
                    ServerMessage(type=WsMessageType.ERROR, payload={"message": "Invalid message"}),
                )
                continue

            await _dispatch(ws, msg)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        logger.exception("WebSocket error")
        manager.disconnect(ws)


async def _dispatch(ws: WebSocket, msg: ClientMessage) -> None:
    match msg.type:
        case WsMessageType.PTT_START:
            await ptt_pipeline.start()

        case WsMessageType.PTT_END:
            await ptt_pipeline.end()

        case WsMessageType.CHAT_SEND:
            text = msg.payload.get("text", "")
            await _handle_chat_send(ws, text)

        case WsMessageType.CAMERA_SUBSCRIBE:
            manager._vision_subscribers.add(ws)
            if not yolo_service.is_running():
                yolo_service.start()
            await manager.send(
                ws,
                ServerMessage(type=WsMessageType.PONG, payload={"subscribed": "camera"}),
            )

        case WsMessageType.CAMERA_UNSUBSCRIBE:
            manager._vision_subscribers.discard(ws)

        case _:
            await manager.send(
                ws,
                ServerMessage(type=WsMessageType.ERROR, payload={"message": f"Unknown type: {msg.type}"}),
            )


async def _handle_chat_send(ws: WebSocket, text: str) -> None:
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


_vision_queue: asyncio.Queue | None = None
_main_loop: asyncio.AbstractEventLoop | None = None


def setup_vision_broadcast() -> None:
    """Register YOLO callback to push vision_frame_meta to subscribers."""
    global _vision_queue, _main_loop
    _vision_queue = asyncio.Queue(maxsize=64)
    _main_loop = asyncio.get_running_loop()

    async def vision_pump() -> None:
        while True:
            ts, detections, w, h = await _vision_queue.get()
            if not manager._vision_subscribers:
                continue
            msg = ServerMessage(
                type=WsMessageType.VISION_FRAME_META,
                payload={
                    "ts": ts,
                    "detections": [d.model_dump() for d in detections],
                    "frame_width": w,
                    "frame_height": h,
                },
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
