from fastapi import APIRouter

from app.services.camera import camera_service
from app.services.llm_client import llm_client
from app.services.scene_memory import scene_memory
from app.services.yolo import yolo_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    llm_ok = await llm_client.health_check()
    return {
        "status": "ok" if llm_ok else "degraded",
        "llm": llm_ok,
        "camera": camera_service.is_active(),
        "yolo": yolo_service.is_running(),
        "scene_memory": scene_memory.stats(),
    }
