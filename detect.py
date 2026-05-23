"""YOLO person detection with optional stereo distance (ELP side-by-side)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

from config import ROOT, Settings, get_settings

try:
    from stereo_depth import StereoDepth
except ImportError:
    StereoDepth = None  # type: ignore[misc, assignment]

PERSON_CLASS = 0


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="YOLO person detection + stereo distance")
    parser.add_argument("--model", default=None, help="YOLO weights (.pt or .engine)")
    parser.add_argument("--camera", type=int, default=settings.camera_device)
    parser.add_argument("--conf", type=float, default=settings.yolo_confidence)
    parser.add_argument("--imgsz", type=int, default=settings.yolo_imgsz)
    parser.add_argument("--skip", type=int, default=settings.yolo_frame_skip, help="Run YOLO every N frames")
    parser.add_argument(
        "--no-stereo",
        action="store_true",
        help="Disable stereo depth even if CAMERA_STEREO=true",
    )
    return parser.parse_args()


def resolve_model_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    if path.suffix == ".pt":
        engine = path.with_suffix(".engine")
        if engine.is_file():
            print(f"Using TensorRT engine: {engine.name}", file=sys.stderr)
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


def draw_detections(
    frame: np.ndarray,
    boxes,
    depth: StereoDepth | None,
) -> np.ndarray:
    out = frame.copy()
    count = 0
    if boxes is None:
        return out

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0]) if box.conf is not None else 0.0
        count += 1

        dist_label = ""
        if depth is not None:
            dist_m = depth.distance_at_bbox(x1, y1, x2, y2)
            if dist_m is not None:
                dist_label = f" {dist_m:.1f}m"
            else:
                dist_label = " ?m"

        label = f"person {conf:.0f}%{dist_label}"
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            out,
            label,
            (x1, max(y1 - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
        )

    cv2.putText(
        out,
        f"persons: {count}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )
    return out


def main() -> None:
    args = parse_args()
    settings = get_settings()

    model_path = resolve_model_path(args.model or settings.yolo_model)
    if not model_path.is_file():
        print(f"Model not found: {model_path}", file=sys.stderr)
        print("Run: bash models/download_models.sh", file=sys.stderr)
        sys.exit(1)

    use_stereo = settings.camera_stereo and not args.no_stereo
    if use_stereo and StereoDepth is None:
        print("Stereo disabled: stereo_depth module unavailable.", file=sys.stderr)
        use_stereo = False

    print(f"Loading {model_path.name} …", file=sys.stderr)
    model = YOLO(str(model_path))
    device = yolo_device()

    cap = open_camera(args.camera, settings.camera_width, settings.camera_height)
    if not cap.isOpened():
        print(f"Could not open camera {args.camera}", file=sys.stderr)
        sys.exit(1)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera: {actual_w}x{actual_h}  YOLO imgsz={args.imgsz}  device={device}", file=sys.stderr)

    stereo: StereoDepth | None = None
    if use_stereo:
        stereo = StereoDepth(
            baseline_m=settings.stereo_baseline_m,
            focal_px=settings.stereo_focal_px,
            max_distance_m=settings.stereo_max_distance_m,
        )
        print(
            f"Stereo depth on (baseline={settings.stereo_baseline_m}m, "
            f"focal={settings.stereo_focal_px}px)",
            file=sys.stderr,
        )

    print("Press Q to quit", file=sys.stderr)
    window = "Arif Detect"
    frame_idx = 0
    frame_count = 0
    last_boxes = None
    fps_t = time.time()
    fps_display = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera read failed", file=sys.stderr)
                break
            frame_idx += 1
            frame_count += 1

            if use_stereo and stereo is not None:
                left, right = stereo.split_side_by_side(frame)
                if frame_idx % settings.stereo_frame_skip == 0:
                    stereo.compute(left, right)
                view = left
            else:
                view = frame

            if frame_idx % max(args.skip, 1) == 0 or last_boxes is None:
                results = model.predict(
                    view,
                    classes=[PERSON_CLASS],
                    conf=args.conf,
                    imgsz=args.imgsz,
                    verbose=False,
                    device=device,
                )
                last_boxes = results[0].boxes

            annotated = draw_detections(view, last_boxes, stereo)

            now = time.time()
            elapsed = now - fps_t
            if elapsed >= 0.5:
                fps_display = frame_count / elapsed
                frame_count = 0
                fps_t = now
            cv2.putText(
                annotated,
                f"fps~{fps_display:.1f}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 200, 0),
                2,
            )

            cv2.imshow(window, annotated)
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
