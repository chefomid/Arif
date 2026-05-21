import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, devices, health, vision
from app.config import get_settings
from app.ui.setup import register_ui
from app.ws.gateway import init_bridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_bridge()
    from app.services.device_manager import device_manager

    device_manager.auto_select()
    # USB cameras on Jetson may enumerate shortly after boot.
    import asyncio

    await asyncio.sleep(1.0)
    device_manager.auto_select()
    logger.info("Arif backend started")
    yield
    from app.services.camera import camera_service
    from app.services.yolo import yolo_service

    yolo_service.stop()
    camera_service.stop()
    logger.info("Arif backend stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Arif", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router, prefix="/api")
    app.include_router(vision.router, prefix="/api")
    app.include_router(devices.router, prefix="/api")
    from app.ws.gateway import router as ws_router

    app.include_router(ws_router)

    register_ui()

    from nicegui import ui

    ui.run_with(app, title="Arif", dark=True)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("app.main:app", host=s.arif_host, port=s.arif_port, reload=s.arif_debug)
