import logging
import time

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

# Energy threshold for silence detection (tuned for 16kHz mono float32)
SILENCE_THRESHOLD = 0.01


class VADService:
    """Trailing silence detector – auto-send after N seconds of silence post-PTT."""

    def __init__(self) -> None:
        self._silence_seconds = get_settings().vad_silence_seconds
        self._last_speech_ts: float | None = None
        self._monitoring = False

    def start_monitoring(self) -> None:
        self._monitoring = True
        self._last_speech_ts = time.time()

    def stop_monitoring(self) -> None:
        self._monitoring = False
        self._last_speech_ts = None

    def process_chunk(self, audio: np.ndarray) -> bool:
        """Returns True when silence duration exceeded and should auto-send."""
        if not self._monitoring:
            return False

        rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
        now = time.time()

        if rms > SILENCE_THRESHOLD:
            self._last_speech_ts = now
            return False

        if self._last_speech_ts is None:
            self._last_speech_ts = now
            return False

        if now - self._last_speech_ts >= self._silence_seconds:
            self._monitoring = False
            return True

        return False

    @property
    def silence_seconds(self) -> float:
        return self._silence_seconds


vad_service = VADService()
