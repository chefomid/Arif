"""Discover and select microphone / camera devices."""

import logging
import re
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)

USB_HINTS = re.compile(
    r"usb|external|webcam|camera|elp|logitech|blue\s*yeti|rode|audio|mic",
    re.I,
)
SKIP_AUDIO = re.compile(r"loopback|stereo\s*mix|mapper|output|speaker", re.I)


@dataclass
class AudioDevice:
    index: int
    name: str
    channels: int
    default_samplerate: float
    is_default: bool
    score: int = 0


@dataclass
class CameraDevice:
    index: int
    name: str
    width: int
    height: int
    score: int = 0


class DeviceManager:
    def __init__(self) -> None:
        settings = get_settings()
        self._mic_index: int | None = settings.mic_device
        self._camera_index: int = settings.camera_device

    @property
    def mic_index(self) -> int | None:
        return self._mic_index

    @property
    def camera_index(self) -> int:
        return self._camera_index

    def get_input_device(self) -> int | None:
        """None = sounddevice default."""
        return self._mic_index

    def list_audio_devices(self) -> list[AudioDevice]:
        try:
            import sounddevice as sd
        except ImportError:
            return []

        default_idx = sd.default.device[0]
        if default_idx is None or default_idx < 0:
            default_idx = None

        result: list[AudioDevice] = []
        for i, dev in enumerate(sd.query_devices()):
            ch = dev.get("max_input_channels", 0)
            if ch < 1:
                continue
            name = dev.get("name", f"Input {i}")
            if SKIP_AUDIO.search(name):
                continue

            score = 0
            if USB_HINTS.search(name):
                score += 10
            if i == default_idx:
                score += 3
            if "microphone" in name.lower() or "mic" in name.lower():
                score += 2

            result.append(
                AudioDevice(
                    index=i,
                    name=name,
                    channels=int(ch),
                    default_samplerate=float(dev.get("default_samplerate", 48000)),
                    is_default=(i == default_idx),
                    score=score,
                )
            )

        result.sort(key=lambda d: (-d.score, d.index))
        return result

    def list_camera_devices(self, max_probe: int = 8) -> list[CameraDevice]:
        import cv2

        result: list[CameraDevice] = []
        for i in range(max_probe):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if _is_windows() else cv2.CAP_ANY)
            if not cap.isOpened():
                cap.release()
                continue

            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            if w < 1 or h < 1:
                continue

            label = f"Camera {i}"
            score = 0
            pixels = w * h
            score += min(pixels // 10000, 20)
            if i > 0:
                score += 3
            if w > h * 1.5:
                score += 5

            result.append(
                CameraDevice(
                    index=i,
                    name=f"{label} ({w}×{h})",
                    width=w,
                    height=h,
                    score=score,
                )
            )

        result.sort(key=lambda d: (-d.score, d.index))
        return result

    def auto_select(self) -> dict:
        """Pick best-guess USB/external mic and highest-quality camera."""
        mics = self.list_audio_devices()
        cams = self.list_camera_devices()

        if mics:
            best_mic = mics[0]
            self._mic_index = best_mic.index
            logger.info("Auto-selected mic [%d] %s", best_mic.index, best_mic.name)
        else:
            self._mic_index = None

        if cams:
            best_cam = cams[0]
            self._camera_index = best_cam.index
            logger.info("Auto-selected camera [%d] %s", best_cam.index, best_cam.name)
        else:
            self._camera_index = get_settings().camera_device

        return self.status()

    def set_mic(self, index: int | None) -> None:
        if index is not None:
            mics = {d.index for d in self.list_audio_devices()}
            if index not in mics:
                raise ValueError(f"Invalid microphone index: {index}")
        self._mic_index = index
        logger.info("Microphone set to %s", index)

    def set_camera(self, index: int) -> None:
        cams = {d.index for d in self.list_camera_devices()}
        if index not in cams:
            raise ValueError(f"Invalid camera index: {index}")
        self._camera_index = index
        logger.info("Camera set to %d", index)

        from app.services.camera import camera_service
        from app.services.yolo import yolo_service

        if camera_service.is_active() or yolo_service.is_running():
            yolo_service.stop()
            camera_service.stop()

    def status(self) -> dict:
        mics = self.list_audio_devices()
        cams = self.list_camera_devices()
        mic_info = next((m for m in mics if m.index == self._mic_index), None)
        cam_info = next((c for c in cams if c.index == self._camera_index), None)

        return {
            "mic": {
                "index": self._mic_index,
                "name": mic_info.name if mic_info else "System default",
            },
            "camera": {
                "index": self._camera_index,
                "name": cam_info.name if cam_info else f"Camera {self._camera_index}",
            },
            "audio_devices": [
                {
                    "index": d.index,
                    "name": d.name,
                    "channels": d.channels,
                    "is_default": d.is_default,
                    "selected": (
                        self._mic_index is not None and d.index == self._mic_index
                    ),
                }
                for d in mics
            ],
            "camera_devices": [
                {
                    "index": d.index,
                    "name": d.name,
                    "width": d.width,
                    "height": d.height,
                    "selected": d.index == self._camera_index,
                }
                for d in cams
            ],
        }


def _is_windows() -> bool:
    import sys

    return sys.platform == "win32"


device_manager = DeviceManager()
