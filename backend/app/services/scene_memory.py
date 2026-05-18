import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from app.config import get_settings
from app.schemas.messages import Detection

logger = logging.getLogger(__name__)


@dataclass
class SceneEvent:
    ts: float
    detections: list[Detection]
    thumbnail: bytes | None = None


@dataclass
class FrameRef:
    ts: float
    jpeg: bytes
    detections: list[Detection] = field(default_factory=list)


class SceneMemory:
    def __init__(self) -> None:
        self._events: deque[SceneEvent] = deque()
        self._keyframes: deque[FrameRef] = deque()
        self._last_summary_ts: float = 0.0
        self._summary_lines: deque[str] = deque(maxlen=120)

    def _max_age_sec(self) -> float:
        return get_settings().scene_memory_minutes * 60

    def _prune(self) -> None:
        now = time.time()
        max_age = self._max_age_sec()
        while self._events and now - self._events[0].ts > max_age:
            self._events.popleft()
        while self._keyframes and now - self._keyframes[0].ts > max_age:
            self._keyframes.popleft()

    def add_event(
        self,
        detections: list[Detection],
        thumbnail: bytes | None = None,
        ts: float | None = None,
    ) -> None:
        ts = ts or time.time()
        self._events.append(SceneEvent(ts=ts, detections=detections, thumbnail=thumbnail))
        self._prune()
        self._maybe_summarize(ts, detections)

    def add_keyframe(self, jpeg: bytes, detections: list[Detection], ts: float | None = None) -> None:
        ts = ts or time.time()
        self._keyframes.append(FrameRef(ts=ts, jpeg=jpeg, detections=detections))
        self._prune()

    def _maybe_summarize(self, ts: float, detections: list[Detection]) -> None:
        settings = get_settings()
        if ts - self._last_summary_ts < settings.scene_summary_interval_sec:
            return
        if not detections:
            return

        self._last_summary_ts = ts
        labels = sorted({d.class_name for d in detections})
        stamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        line = f"{stamp} – {', '.join(labels)}"
        self._summary_lines.append(line)

    def get_rolling_summary(self, max_lines: int = 30) -> str:
        if not self._summary_lines:
            return ""
        lines = list(self._summary_lines)[-max_lines:]
        return "\n".join(lines)

    def query_recent(self, minutes: float = 5, class_name: str | None = None) -> str:
        self._prune()
        cutoff = time.time() - minutes * 60
        results: list[str] = []

        for event in self._events:
            if event.ts < cutoff:
                continue
            dets = event.detections
            if class_name:
                dets = [d for d in dets if d.class_name.lower() == class_name.lower()]
            if not dets:
                continue
            stamp = datetime.fromtimestamp(event.ts).strftime("%H:%M:%S")
            labels = ", ".join(
                f"{d.class_name}({d.confidence:.0%})" for d in dets
            )
            results.append(f"[{stamp}] {labels}")

        return "\n".join(results) if results else "No matching detections in that time range."

    def query_by_class(self, class_name: str, minutes: float = 10) -> str:
        return self.query_recent(minutes=minutes, class_name=class_name)

    def get_keyframe_near(self, ts: float, tolerance_sec: float = 2.0) -> FrameRef | None:
        best: FrameRef | None = None
        best_delta = tolerance_sec
        for kf in self._keyframes:
            delta = abs(kf.ts - ts)
            if delta < best_delta:
                best_delta = delta
                best = kf
        return best

    def stats(self) -> dict:
        return {
            "events": len(self._events),
            "keyframes": len(self._keyframes),
            "summary_lines": len(self._summary_lines),
        }


scene_memory = SceneMemory()
