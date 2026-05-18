from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    arif_host: str = "0.0.0.0"
    arif_port: int = 8000
    arif_debug: bool = False

    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_model: str = "nemotron"
    llm_api_key: str = "not-needed"

    whisper_model: str = "tiny.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    vad_silence_seconds: float = 3.0
    vad_sample_rate: int = 16000

    mic_device: int | None = None

    camera_device: int = 0
    camera_width: int = 1600
    camera_height: int = 600
    camera_stereo: bool = True
    camera_fps: int = 30

    yolo_model: str = "models/yolo11n.engine"
    yolo_confidence: float = 0.4
    yolo_fps_cap: int = 8

    scene_memory_minutes: int = 10
    scene_keyframe_fps: int = 1
    scene_summary_interval_sec: int = 5

    gpu_temp_throttle_c: int = 80
    yolo_fps_min: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
