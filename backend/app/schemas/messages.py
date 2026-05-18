from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WsMessageType(StrEnum):
    # Client -> server
    PTT_START = "ptt_start"
    PTT_END = "ptt_end"
    CHAT_SEND = "chat_send"
    CAMERA_SUBSCRIBE = "camera_subscribe"
    CAMERA_UNSUBSCRIBE = "camera_unsubscribe"

    # Server -> client
    STT_PARTIAL = "stt_partial"
    STT_FINAL = "stt_final"
    CHAT_TOKEN = "chat_token"
    CHAT_DONE = "chat_done"
    VISION_FRAME_META = "vision_frame_meta"
    ERROR = "error"
    PONG = "pong"


class Detection(BaseModel):
    class_name: str
    confidence: float
    x: float
    y: float
    w: float
    h: float


class DetectionFrame(BaseModel):
    ts: float
    detections: list[Detection]
    frame_width: int = 0
    frame_height: int = 0


class ChatMessage(BaseModel):
    role: str
    content: str


class ClientMessage(BaseModel):
    v: int = 1
    type: WsMessageType
    payload: dict[str, Any] = Field(default_factory=dict)


class ServerMessage(BaseModel):
    v: int = 1
    type: WsMessageType
    payload: dict[str, Any] = Field(default_factory=dict)
