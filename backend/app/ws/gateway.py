import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.messages import ClientMessage, ServerMessage, WsMessageType
from app.ui import handlers
from app.ui.bridge import register_connection_manager, register_ptt_callbacks, setup_vision_broadcast
from app.ui.state import state

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

    async def broadcast_all(self, msg: ServerMessage) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await self.send(ws, msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

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
register_connection_manager(manager)


def _parse_client(data: str) -> ClientMessage | None:
    try:
        raw = json.loads(data)
        return ClientMessage(**raw)
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_gateway(ws: WebSocket):
    await manager.connect(ws)

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
            state.mic_hot = True
            state.notify()
            await handlers.handle_ptt_start()

        case WsMessageType.PTT_END:
            state.mic_hot = False
            state.notify()
            await handlers.handle_ptt_end()

        case WsMessageType.CHAT_SEND:
            text = msg.payload.get("text", "")
            await handlers.handle_chat_send_ws(ws, text, manager)

        case WsMessageType.CAMERA_SUBSCRIBE:
            await handlers.handle_camera_subscribe_ws(ws, manager)

        case WsMessageType.CAMERA_UNSUBSCRIBE:
            handlers.handle_camera_unsubscribe_ws(ws, manager)

        case _:
            await manager.send(
                ws,
                ServerMessage(type=WsMessageType.ERROR, payload={"message": f"Unknown type: {msg.type}"}),
            )


def init_bridge() -> None:
    """Call from FastAPI lifespan after event loop is running."""
    register_ptt_callbacks()
    setup_vision_broadcast(manager)
