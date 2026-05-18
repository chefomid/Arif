import asyncio

from fastapi import APIRouter, Query
from fastapi.responses import Response, StreamingResponse

from app.services.camera import camera_service
from app.services.scene_memory import scene_memory
from app.services.yolo import yolo_service

router = APIRouter(prefix="/vision", tags=["vision"])


@router.get("/memory/query")
async def query_memory(
    minutes: float = Query(5, ge=0.1, le=60),
    class_name: str | None = None,
):
    if class_name:
        result = scene_memory.query_by_class(class_name, minutes=minutes)
    else:
        result = scene_memory.query_recent(minutes=minutes)
    return {"result": result, "minutes": minutes}


@router.get("/memory/summary")
async def memory_summary():
    return {"summary": scene_memory.get_rolling_summary()}


@router.post("/camera/start")
async def start_camera():
    ok = yolo_service.start()
    return {"ok": ok, "camera": camera_service.is_active(), "yolo": yolo_service.is_running()}


@router.post("/camera/stop")
async def stop_camera():
    yolo_service.stop()
    camera_service.stop()
    return {"ok": True}


async def _mjpeg_generator():
    boundary = b"--frame"
    while True:
        jpeg = camera_service.get_mjpeg_frame()
        if jpeg:
            yield boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        await asyncio.sleep(1.0 / 15)


@router.get("/camera/mjpeg")
async def mjpeg_stream():
    if not camera_service.is_active():
        camera_service.start()
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/camera/snapshot")
async def snapshot():
    jpeg = camera_service.get_mjpeg_frame()
    if not jpeg:
        return Response(status_code=503, content="Camera not available")
    return Response(content=jpeg, media_type="image/jpeg")
