from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chat import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def send_chat(req: ChatRequest):
    reply = await chat_service.send(req.message)
    return ChatResponse(reply=reply)


@router.delete("/history")
async def clear_history():
    chat_service.clear_history()
    return {"ok": True}
