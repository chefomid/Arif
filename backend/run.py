"""Run Arif: FastAPI + NiceGUI UI on one port."""
import uvicorn

from app.config import get_settings
from app.main import app

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.arif_host,
        port=settings.arif_port,
        reload=settings.arif_debug,
    )
