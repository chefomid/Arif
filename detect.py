"""Webcam YOLO person detection with OpenCV GUI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

from config import ROOT, get_settings

PERSON_CLASS = 0  # COCO "person"


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run YOLO person detection on webcam")
    parser.add_argument(
        "--model",
        default=settings.yolo_model,
        help=f"YOLO weights (default: {settings.yolo_model})",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=settings.camera_device,
        help=f"Camera index (default: {settings.camera_device})",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=settings.yolo_confidence,
        help=f"Confidence threshold (default: {settings.yolo_confidence})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    if not model_path.exists():
        print(f"Model not found: {model_path}", file=sys.stderr)
        print("Run: bash models/download_models.sh", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {model_path} …")
    model = YOLO(str(model_path))

    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
    cap = cv2.VideoCapture(args.camera, backend)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Could not open camera {args.camera}", file=sys.stderr)
        sys.exit(1)

    print("Detecting person — press Q to quit")
    window = "Arif Detect (person)"
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera read failed", file=sys.stderr)
                break

            results = model(frame, classes=[PERSON_CLASS], conf=args.conf, verbose=False)
            annotated = results[0].plot()
            count = len(results[0].boxes) if results[0].boxes is not None else 0
            cv2.putText(
                annotated,
                f"persons: {count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
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
