import asyncio
import logging
import queue
import threading
from collections.abc import Callable

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class AudioCaptureService:
    """Captures microphone audio while PTT is held via sounddevice."""

    def __init__(self) -> None:
        self._sample_rate = get_settings().vad_sample_rate
        self._recording = False
        self._stream = None
        self._chunks: queue.Queue[np.ndarray] = queue.Queue()
        self._buffer: list[np.ndarray] = []
        self._on_chunk: Callable[[np.ndarray], None] | None = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            logger.warning("Audio status: %s", status)
        if self._recording:
            chunk = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
            self._chunks.put(chunk)
            self._buffer.append(chunk)

    def start(self, on_chunk: Callable[[np.ndarray], None] | None = None) -> None:
        if self._recording:
            return

        import sounddevice as sd

        from app.services.device_manager import device_manager

        self._on_chunk = on_chunk
        self._recording = True
        self._buffer.clear()

        device = device_manager.get_input_device()
        kwargs: dict = {
            "samplerate": self._sample_rate,
            "channels": 1,
            "dtype": "float32",
            "callback": self._audio_callback,
            "blocksize": int(self._sample_rate * 0.1),
        }
        if device is not None:
            kwargs["device"] = device

        self._stream = sd.InputStream(**kwargs)
        self._stream.start()
        logger.info("Audio capture started at %d Hz", self._sample_rate)

    def stop(self) -> np.ndarray:
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._buffer:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(self._buffer)
        self._buffer.clear()
        logger.info("Audio capture stopped, %d samples", len(audio))
        return audio

    def drain_chunks(self) -> list[np.ndarray]:
        chunks: list[np.ndarray] = []
        while not self._chunks.empty():
            try:
                chunks.append(self._chunks.get_nowait())
            except queue.Empty:
                break
        return chunks

    async def pump_chunks(self, on_chunk: Callable[[np.ndarray], None]) -> None:
        while self._recording:
            chunks = self.drain_chunks()
            for chunk in chunks:
                on_chunk(chunk)
            await asyncio.sleep(0.05)

    def get_full_buffer(self) -> np.ndarray:
        if not self._buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._buffer)


audio_capture = AudioCaptureService()
