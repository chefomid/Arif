"""Run backend: python run.py from backend/ directory."""
import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.arif_host,
        port=s.arif_port,
        reload=s.arif_debug,
    )
