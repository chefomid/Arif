"""Stereo disparity → depth for side-by-side USB cameras (e.g. ELP)."""
from __future__ import annotations

import numpy as np

try:
    import cv2
except ImportError as exc:
    raise ImportError("opencv-python is required for stereo depth") from exc


class StereoDepth:
    """Compute depth (meters) from rectified left/right grayscale pair."""

    def __init__(
        self,
        baseline_m: float,
        focal_px: float,
        num_disparities: int = 64,
        block_size: int = 5,
        max_distance_m: float = 10.0,
    ) -> None:
        self.baseline_m = baseline_m
        self.focal_px = focal_px
        self.max_distance_m = max_distance_m
        block_size = max(block_size | 1, 3)
        self._stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=max(16, num_disparities // 16 * 16),
            blockSize=block_size,
            P1=8 * 3 * block_size**2,
            P2=32 * 3 * block_size**2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32,
        )
        self._depth_m: np.ndarray | None = None

    @staticmethod
    def split_side_by_side(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h, w = frame.shape[:2]
        mid = w // 2
        left = frame[:, :mid]
        right = frame[:, mid:]
        if right.shape[1] != left.shape[1]:
            right = cv2.resize(right, (left.shape[1], left.shape[0]))
        return left, right

    def compute(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        if left.shape[:2] != right.shape[:2]:
            right = cv2.resize(right, (left.shape[1], left.shape[0]))

        scale = 0.5
        small_l = cv2.resize(left, None, fx=scale, fy=scale)
        small_r = cv2.resize(right, None, fx=scale, fy=scale)
        gray_l = cv2.cvtColor(small_l, cv2.COLOR_BGR2GRAY)
        gray_r = cv2.cvtColor(small_r, cv2.COLOR_BGR2GRAY)

        disp = self._stereo.compute(gray_l, gray_r).astype(np.float32) / 16.0
        disp[disp <= 0.5] = np.nan

        depth_small = (self.focal_px * scale * self.baseline_m) / disp
        depth_small = np.clip(depth_small, 0.1, self.max_distance_m)

        self._depth_m = cv2.resize(
            depth_small,
            (left.shape[1], left.shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )
        return self._depth_m

    @property
    def depth_m(self) -> np.ndarray | None:
        return self._depth_m

    def distance_at_bbox(self, x1: int, y1: int, x2: int, y2: int) -> float | None:
        if self._depth_m is None:
            return None
        h, w = self._depth_m.shape
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        pad = 8
        patch = self._depth_m[
            max(0, cy - pad) : min(h, cy + pad + 1),
            max(0, cx - pad) : min(w, cx + pad + 1),
        ]
        valid = patch[np.isfinite(patch) & (patch > 0.15) & (patch < self.max_distance_m)]
        if valid.size < 3:
            return None
        return float(np.median(valid))
