import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

import numpy as np

from app.config import get_settings
from app.services.audio_capture import audio_capture
from app.services.stt import stt_service
from app.services.vad import vad_service

logger = logging.getLogger(__name__)


class PTTPipeline:
    """Orchestrates push-to-talk: capture → partial STT → VAD auto-send."""

    def __init__(self) -> None:
        self._active = False
        self._accumulated: list[np.ndarray] = []
        self._partial_task: asyncio.Task | None = None
        self._vad_task: asyncio.Task | None = None
        self._on_partial: Callable[[str], Awaitable[None]] | None = None
        self._on_final: Callable[[str], Awaitable[None]] | None = None
        self._on_auto_send: Callable[[str], Awaitable[None]] | None = None

    def set_callbacks(
        self,
        on_partial: Callable[[str], Awaitable[None]],
        on_final: Callable[[str], Awaitable[None]],
        on_auto_send: Callable[[str], Awaitable[None]],
    ) -> None:
        self._on_partial = on_partial
        self._on_final = on_final
        self._on_auto_send = on_auto_send

    async def start(self) -> None:
        if self._active:
            return
        if self._vad_task and not self._vad_task.done():
            self._vad_task.cancel()
        self._active = True
        self._accumulated.clear()
        vad_service.stop_monitoring()

        def on_chunk(chunk: np.ndarray) -> None:
            self._accumulated.append(chunk)

        audio_capture.start(on_chunk=on_chunk)
        self._partial_task = asyncio.create_task(self._partial_loop())

    async def end(self) -> None:
        if not self._active:
            return
        self._active = False
        audio_capture.stop()

        if self._partial_task:
            self._partial_task.cancel()
            try:
                await self._partial_task
            except asyncio.CancelledError:
                pass
            self._partial_task = None

        audio = self._get_accumulated()
        text = ""
        if len(audio) > 0:
            try:
                text = await asyncio.to_thread(
                    stt_service.transcribe,
                    audio,
                    audio_capture.sample_rate,
                )
            except Exception:
                logger.exception("Final STT failed")

        if self._on_final and text:
            await self._on_final(text)

        self._pending_text = text
        self._pending_audio = audio
        vad_service.start_monitoring()
        self._vad_task = asyncio.create_task(self._vad_wait_loop())

    def _get_accumulated(self) -> np.ndarray:
        chunks = list(self._accumulated) + audio_capture.drain_chunks()
        if not chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(chunks)

    async def _partial_loop(self) -> None:
        last_len = 0
        while self._active:
            await asyncio.sleep(0.4)
            audio = self._get_accumulated()
            if len(audio) < audio_capture.sample_rate * 0.3:
                continue
            if len(audio) == last_len:
                continue
            last_len = len(audio)

            try:
                partial = await asyncio.to_thread(
                    stt_service.transcribe_partial,
                    audio.copy(),
                    audio_capture.sample_rate,
                )
                if partial and self._on_partial:
                    await self._on_partial(partial)
            except Exception:
                logger.exception("Partial STT failed")

    async def _vad_wait_loop(self) -> None:
        """After PTT release, monitor mic for trailing speech; auto-send after silence."""
        settings = get_settings()
        trailing_chunks: list[np.ndarray] = []
        stream = None

        try:
            import sounddevice as sd

            def callback(indata, frames, time_info, status):
                chunk = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
                trailing_chunks.append(chunk)
                vad_service.process_chunk(chunk)

            from app.services.device_manager import device_manager

            vad_kwargs: dict = {
                "samplerate": audio_capture.sample_rate,
                "channels": 1,
                "dtype": "float32",
                "callback": callback,
                "blocksize": int(audio_capture.sample_rate * 0.1),
            }
            mic = device_manager.get_input_device()
            if mic is not None:
                vad_kwargs["device"] = mic

            stream = sd.InputStream(**vad_kwargs)
            stream.start()

            while vad_service._monitoring:
                await asyncio.sleep(0.1)

        except Exception:
            logger.exception("VAD monitor failed, using timeout fallback")
            await asyncio.sleep(settings.vad_silence_seconds)
        finally:
            if stream:
                stream.stop()
                stream.close()
            vad_service.stop_monitoring()

        final_text = getattr(self, "_pending_text", "")
        pending_audio = getattr(self, "_pending_audio", np.array([], dtype=np.float32))

        if trailing_chunks:
            trailing = np.concatenate(trailing_chunks)
            combined = (
                np.concatenate([pending_audio, trailing])
                if len(pending_audio)
                else trailing
            )
            if len(combined) > audio_capture.sample_rate * 0.3:
                try:
                    final_text = await asyncio.to_thread(
                        stt_service.transcribe,
                        combined,
                        audio_capture.sample_rate,
                    )
                except Exception:
                    logger.exception("VAD trailing STT failed")

        if final_text and self._on_auto_send:
            await self._on_auto_send(final_text)


ptt_pipeline = PTTPipeline()
