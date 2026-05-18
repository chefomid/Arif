from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.device_manager import device_manager

router = APIRouter(prefix="/devices", tags=["devices"])


class SelectMicRequest(BaseModel):
    index: int | None = None


class SelectCameraRequest(BaseModel):
    index: int


@router.get("")
async def list_devices():
    return device_manager.status()


@router.post("/auto")
async def auto_select():
    return device_manager.auto_select()


@router.post("/mic")
async def select_mic(req: SelectMicRequest):
    try:
        device_manager.set_mic(req.index)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return device_manager.status()


@router.post("/camera")
async def select_camera(req: SelectCameraRequest):
    try:
        device_manager.set_camera(req.index)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return device_manager.status()
