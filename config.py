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
    yolo_imgsz: int = 416
    yolo_frame_skip: int = 2
    camera_device: int = 0
    camera_width: int = 1600
    camera_height: int = 600
    camera_stereo: bool = True
    stereo_baseline_m: float = 0.06
    stereo_focal_px: float = 500.0
    stereo_max_distance_m: float = 10.0
    stereo_frame_skip: int = 2

    # LLM chat — light (fast) vs heavy (Nemotron)
    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_api_key: str = "not-needed"
    llm_gpu_layers: int = 0
    llm_ready_timeout_sec: int = 0  # 0 = auto

    llm_light_model_path: str = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    llm_light_model: str = "light"
    llm_light_ctx_size: int = 512

    llm_heavy_model_path: str = "models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf"
    llm_heavy_model: str = "nemotron"
    llm_heavy_ctx_size: int = 1024

    # Active model (set by chat.py after user picks 1 or 2)
    llm_model_path: str = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    llm_model: str = "light"
    llm_ctx_size: int = 512


@lru_cache
def get_settings() -> Settings:
    return Settings()


def settings_for_choice(settings: Settings, choice: str) -> tuple[Settings, str]:
    """Return settings configured for light (1) or heavy (2) model."""
    if choice == "2":
        return settings.model_copy(
            update={
                "llm_model_path": settings.llm_heavy_model_path,
                "llm_model": settings.llm_heavy_model,
                "llm_ctx_size": settings.llm_heavy_ctx_size,
            }
        ), "heavy (Nemotron 4B)"
    return settings.model_copy(
        update={
            "llm_model_path": settings.llm_light_model_path,
            "llm_model": settings.llm_light_model,
            "llm_ctx_size": settings.llm_light_ctx_size,
        }
    ), "light (Qwen 0.5B)"
