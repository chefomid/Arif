import logging
import time

from app.config import get_settings

logger = logging.getLogger(__name__)


class ResourceOrchestrator:
    """Caps vision FPS and gates heavy model usage based on thermal/load."""

    def __init__(self) -> None:
        settings = get_settings()
        self._yolo_fps_cap = settings.yolo_fps_cap
        self._yolo_fps_min = settings.yolo_fps_min
        self._gpu_temp_throttle = settings.gpu_temp_throttle_c
        self._whisper_active = False
        self._last_yolo_frame = 0.0

    @property
    def yolo_fps_cap(self) -> int:
        return self._yolo_fps_cap

    def set_whisper_active(self, active: bool) -> None:
        self._whisper_active = active
        if active:
            self._yolo_fps_cap = max(
                self._yolo_fps_min,
                get_settings().yolo_fps_cap // 2,
            )
        else:
            self._yolo_fps_cap = get_settings().yolo_fps_cap

    def should_run_yolo(self) -> bool:
        interval = 1.0 / max(self._yolo_fps_cap, 1)
        now = time.time()
        if now - self._last_yolo_frame >= interval:
            self._last_yolo_frame = now
            return True
        return False

    def update_gpu_temp(self, temp_c: float | None) -> None:
        if temp_c is None:
            return
        if temp_c >= self._gpu_temp_throttle:
            self._yolo_fps_cap = self._yolo_fps_min
            logger.warning("GPU temp %.1fC – throttling YOLO to %d FPS", temp_c, self._yolo_fps_cap)
        elif not self._whisper_active:
            self._yolo_fps_cap = get_settings().yolo_fps_cap

    def read_gpu_temp(self) -> float | None:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000.0
        except (FileNotFoundError, OSError, ValueError):
            return None


orchestrator = ResourceOrchestrator()
