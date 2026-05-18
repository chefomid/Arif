import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, devices, health, vision
from app.config import ROOT_DIR, get_settings
from app.ws.gateway import router as ws_router, setup_vision_broadcast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_vision_broadcast()
    from app.services.device_manager import device_manager

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
    app.include_router(ws_router)

    @app.get("/")
    async def root():
        from fastapi.responses import FileResponse

        index = ROOT_DIR / "frontend" / "dist" / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"message": "Arif API – build frontend with: cd frontend && npm run build"}

    frontend_dist = ROOT_DIR / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("app.main:app", host=s.arif_host, port=s.arif_port, reload=s.arif_debug)
