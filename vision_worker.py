"""Background camera + YOLO loop; thread-safe snapshot for chat."""
from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
from ultralytics import YOLO

from config import ROOT, Settings, get_settings

try:
    from stereo_depth import StereoDepth
except ImportError:
    StereoDepth = None  # type: ignore[misc, assignment]

PERSON_CLASS = 0


def resolve_model_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    if path.suffix == ".pt":
        engine = path.with_suffix(".engine")
        if engine.is_file():
            return engine
    return path


def open_camera(device: int, width: int, height: int) -> cv2.VideoCapture:
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
    cap = cv2.VideoCapture(device, backend)
    if width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        cap = cv2.VideoCapture(device)
    return cap


def yolo_device() -> str | int:
    try:
        import torch

        if torch.cuda.is_available():
            return 0
    except ImportError:
        pass
    return "cpu"


@dataclass
class VisionSnapshot:
    person_count: int = 0
    distances_m: list[float] = field(default_factory=list)
    updated_at: float = 0.0
    camera_ok: bool = False
    error: str = ""

    def age_seconds(self) -> float:
        if self.updated_at <= 0:
            return float("inf")
        return time.time() - self.updated_at

    def to_context(self) -> str:
        if not self.camera_ok:
            return f"Camera: not available ({self.error or 'unknown error'})"
        age = self.age_seconds()
        stale = " (stale)" if age > 3.0 else ""
        if self.person_count == 0:
            return f"Camera: no person detected{stale} (updated {age:.1f}s ago)"
        parts = [f"Camera: {self.person_count} person(s) detected{stale}"]
        if self.distances_m:
            nearest = min(self.distances_m)
            parts.append(f"nearest ~{nearest:.1f} m")
            if len(self.distances_m) > 1:
                others = ", ".join(f"{d:.1f}m" for d in sorted(self.distances_m))
                parts.append(f"distances: {others}")
        parts.append(f"updated {age:.1f}s ago")
        return ". ".join(parts) + "."


class VisionWorker:
    """Runs YOLO on camera frames in a background thread."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._lock = threading.Lock()
        self._snapshot = VisionSnapshot()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def snapshot(self) -> VisionSnapshot:
        with self._lock:
            return VisionSnapshot(
                person_count=self._snapshot.person_count,
                distances_m=list(self._snapshot.distances_m),
                updated_at=self._snapshot.updated_at,
                camera_ok=self._snapshot.camera_ok,
                error=self._snapshot.error,
            )

    def _set_snapshot(self, **kwargs: object) -> None:
        with self._lock:
            for key, val in kwargs.items():
                setattr(self._snapshot, key, val)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="vision-worker", daemon=True)
        self._thread.start()

        for _ in range(50):
            snap = self.snapshot()
            if snap.camera_ok or snap.error:
                break
            time.sleep(0.1)

        snap = self.snapshot()
        if not snap.camera_ok:
            raise RuntimeError(snap.error or "Camera failed to start")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        settings = self._settings
        model_path = resolve_model_path(settings.yolo_model)
        if not model_path.is_file():
            self._set_snapshot(camera_ok=False, error=f"Model missing: {model_path}")
            return

        use_stereo = settings.camera_stereo and StereoDepth is not None
        stereo: StereoDepth | None = None
        if use_stereo:
            stereo = StereoDepth(
                baseline_m=settings.stereo_baseline_m,
                focal_px=settings.stereo_focal_px,
                max_distance_m=settings.stereo_max_distance_m,
            )

        cap: cv2.VideoCapture | None = None
        try:
            model = YOLO(str(model_path))
            device = yolo_device()
            cap = open_camera(settings.camera_device, settings.camera_width, settings.camera_height)
            if not cap.isOpened():
                self._set_snapshot(camera_ok=False, error=f"Could not open camera {settings.camera_device}")
                return

            self._set_snapshot(camera_ok=True, error="", updated_at=time.time())
            frame_idx = 0
            last_boxes = None

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    self._set_snapshot(camera_ok=False, error="Camera read failed")
                    break
                frame_idx += 1

                if use_stereo and stereo is not None:
                    left, right = stereo.split_side_by_side(frame)
                    if frame_idx % settings.stereo_frame_skip == 0:
                        stereo.compute(left, right)
                    view = left
                else:
                    view = frame

                if frame_idx % max(settings.yolo_frame_skip, 1) == 0 or last_boxes is None:
                    results = model.predict(
                        view,
                        classes=[PERSON_CLASS],
                        conf=settings.yolo_confidence,
                        imgsz=settings.yolo_imgsz,
                        verbose=False,
                        device=device,
                    )
                    last_boxes = results[0].boxes

                count = 0
                distances: list[float] = []
                if last_boxes is not None:
                    for box in last_boxes:
                        count += 1
                        if stereo is not None:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            d = stereo.distance_at_bbox(x1, y1, x2, y2)
                            if d is not None:
                                distances.append(d)

                self._set_snapshot(
                    person_count=count,
                    distances_m=distances,
                    updated_at=time.time(),
                    camera_ok=True,
                    error="",
                )
        except Exception as exc:
            self._set_snapshot(camera_ok=False, error=str(exc))
        finally:
            if cap is not None:
                cap.release()
