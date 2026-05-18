import logging
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any

import cv2
import numpy as np

from app.config import ROOT_DIR, get_settings
from app.schemas.messages import Detection
from app.services.camera import camera_service
from app.services.orchestrator import orchestrator
from app.services.scene_memory import scene_memory

logger = logging.getLogger(__name__)


class YOLOService:
    """YOLO11 object detection loop with TensorRT/PyTorch fallback."""

    def __init__(self) -> None:
        self._model = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._subscribers: list[Callable[[float, list[Detection], int, int], Awaitable[None] | None]] = []
        self._last_keyframe_ts = 0.0

    def _load_model(self) -> None:
        if self._model is not None:
            return

        settings = get_settings()
        model_path = ROOT_DIR / settings.yolo_model

        try:
            from ultralytics import YOLO

            if model_path.exists():
                logger.info("Loading YOLO from %s", model_path)
                self._model = YOLO(str(model_path))
            else:
                logger.warning(
                    "YOLO engine not found at %s, using yolo11n.pt (download on first run)",
                    model_path,
                )
                self._model = YOLO("yolo11n.pt")
        except ImportError as exc:
            raise RuntimeError("ultralytics not installed") from exc

    def _parse_results(self, results, frame_w: int, frame_h: int) -> list[Detection]:
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                name = result.names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        class_name=name,
                        confidence=conf,
                        x=x1 / frame_w,
                        y=y1 / frame_h,
                        w=(x2 - x1) / frame_w,
                        h=(y2 - y1) / frame_h,
                    )
                )
        return detections

    def _inference_loop(self) -> None:
        settings = get_settings()
        keyframe_interval = 1.0 / max(settings.scene_keyframe_fps, 1)

        while self._running:
            if not orchestrator.should_run_yolo():
                time.sleep(0.02)
                continue

            frame = camera_service.get_left_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            orchestrator.update_gpu_temp(orchestrator.read_gpu_temp())

            h, w = frame.shape[:2]
            try:
                self._load_model()
                results = self._model.predict(
                    frame,
                    conf=settings.yolo_confidence,
                    verbose=False,
                )
                detections = self._parse_results(results, w, h)
            except Exception:
                logger.exception("YOLO inference failed")
                time.sleep(0.5)
                continue

            ts = time.time()
            thumb = None
            if detections:
                small = cv2.resize(frame, (160, int(160 * h / w)))
                _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                thumb = buf.tobytes()

            scene_memory.add_event(detections, thumbnail=thumb, ts=ts)

            if ts - self._last_keyframe_ts >= keyframe_interval and thumb:
                self._last_keyframe_ts = ts
                scene_memory.add_keyframe(thumb, detections, ts=ts)

            for cb in self._subscribers:
                try:
                    result = cb(ts, detections, w, h)
                    if hasattr(result, "__await__"):
                        pass
                except Exception:
                    logger.exception("YOLO subscriber callback failed")

            time.sleep(0.01)

    def start(self) -> bool:
        if self._running:
            return True
        if not camera_service.start():
            return False
        self._running = True
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()
        logger.info("YOLO inference loop started")
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def subscribe(self, callback) -> None:
        self._subscribers.append(callback)

    def is_running(self) -> bool:
        return self._running


yolo_service = YOLOService()
