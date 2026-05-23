"""Shared settings loaded from .env (optional)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # YOLO detection
    yolo_model: str = "models/yolo11n.pt"
    yolo_confidence: float = 0.4
    camera_device: int = 0

    # LLM chat (llama-server)
    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_model: str = "nemotron"
    llm_api_key: str = "not-needed"


@lru_cache
def get_settings() -> Settings:
    return Settings()
