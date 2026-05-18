import logging
import tempfile
from pathlib import Path

import numpy as np

from app.config import get_settings
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-text via faster-whisper with lazy model loading."""

    def __init__(self) -> None:
        self._model = None
        self._settings = get_settings()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "Loading Whisper model %s on %s",
                self._settings.whisper_model,
                self._settings.whisper_device,
            )
            self._model = WhisperModel(
                self._settings.whisper_model,
                device=self._settings.whisper_device,
                compute_type=self._settings.whisper_compute_type,
            )
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            ) from exc

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if len(audio) == 0:
            return ""

        self._ensure_model()
        orchestrator.set_whisper_active(True)
        try:
            import wave

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = Path(f.name)
            pcm = (audio * 32767).astype(np.int16)
            with wave.open(str(path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm.tobytes())

            segments, _ = self._model.transcribe(
                str(path),
                beam_size=1,
                vad_filter=True,
                language="en",
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            path.unlink(missing_ok=True)
            return text
        finally:
            orchestrator.set_whisper_active(False)

    def transcribe_partial(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if len(audio) < sample_rate * 0.3:
            return ""
        return self.transcribe(audio, sample_rate)


stt_service = STTService()
