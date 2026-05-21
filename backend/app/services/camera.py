import logging
import threading
import time
from typing import Any

import cv2
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class CameraService:
    """Captures frames from ELP stereo USB camera via OpenCV/V4L2."""

    def __init__(self) -> None:
        settings = get_settings()
        self._width = settings.camera_width
        self._height = settings.camera_height
        self._stereo = settings.camera_stereo
        self._fps = settings.camera_fps
        self._device = settings.camera_device
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._latest_left: np.ndarray | None = None
        self._latest_right: np.ndarray | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    def _refresh_config(self) -> None:
        from app.services.device_manager import device_manager

        self._device = device_manager.camera_index

    def open(self) -> bool:
        if self._cap and self._cap.isOpened():
            return True

        self._refresh_config()
        import sys

        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
        self._cap = cv2.VideoCapture(self._device, backend)
        if not self._cap.isOpened():
            from app.services.device_manager import device_manager

            logger.warning(
                "Failed to open camera %s — re-scanning devices",
                self._device,
            )
            device_manager.auto_select()
            self._refresh_config()
            if self._cap:
                self._cap.release()
            self._cap = cv2.VideoCapture(self._device, backend)
        if not self._cap.isOpened():
            logger.error("Failed to open camera device %s", self._device)
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap.set(cv2.CAP_PROP_FPS, self._fps)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info("Camera opened: %dx%d @ device %s", actual_w, actual_h, self._device)
        return True

    def _split_stereo(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
        h, w = frame.shape[:2]
        if self._stereo and w > h:
            mid = w // 2
            return frame[:, :mid], frame[:, mid:]
        return frame, None

    def _capture_loop(self) -> None:
        while self._running:
            if not self._cap or not self._cap.isOpened():
                time.sleep(0.1)
                continue

            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            left, right = self._split_stereo(frame)
            with self._lock:
                self._latest_frame = frame
                self._latest_left = left
                self._latest_right = right

            time.sleep(1.0 / max(self._fps, 1))

    def start(self) -> bool:
        if self._running:
            return True
        if not self.open():
            return False
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap:
            self._cap.release()
            self._cap = None

    def get_left_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._latest_left.copy() if self._latest_left is not None else None

    def get_full_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def encode_jpeg(self, frame: np.ndarray, quality: int = 80) -> bytes:
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    def get_mjpeg_frame(self) -> bytes | None:
        frame = self.get_full_frame() or self.get_left_frame()
        if frame is None:
            return None
        return self.encode_jpeg(frame)

    def is_active(self) -> bool:
        return self._running and self._cap is not None and self._cap.isOpened()


camera_service = CameraService()
