from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time
from typing import TYPE_CHECKING

try:
    import cv2
    import numpy as np
except ImportError:  # Decision logic remains testable on non-vision control hosts.
    cv2 = None
    np = None

from .config import AppConfig, MonitorConfig
from .octoprint import OctoPrintClient

if TYPE_CHECKING:
    from .capture import CapturedFrame


@dataclass(frozen=True)
class CameraObservation:
    camera: str
    path: str
    quality_passed: bool
    failure_score: float | None
    shift_px: float | None
    rotation_deg: float | None
    camera_stable: bool | None


@dataclass(frozen=True)
class MonitorDecision:
    printing: bool
    severity: str
    pause_requested: bool
    agreeing_cameras: tuple[str, ...]
    confirmation_count: int
    reasons: tuple[str, ...]


class FailureModel:
    """Local ONNX print-failure detector; frames never leave the machine."""

    def __init__(self, path: Path):
        _require_vision()
        try:
            import onnxruntime as ort
        except ImportError as error:
            raise RuntimeError("onnxruntime is required when monitor.model_path is set") from error
        self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def score(self, image: np.ndarray) -> float:
        rgb = cv2.cvtColor(cv2.resize(image, (416, 416)), cv2.COLOR_BGR2RGB)
        tensor = np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1))[None, ...]
        outputs = self.session.run(None, {self.input_name: tensor})
        confidences = np.asarray(outputs[1])
        return float(np.max(confidences)) if confidences.size else 0.0


def camera_motion(reference: np.ndarray, current: np.ndarray) -> tuple[float, float] | None:
    """Estimate fixed-camera translation and rotation from robust scene features."""
    _require_vision()
    reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    detector = cv2.ORB_create(nfeatures=2500)
    first, first_descriptors = detector.detectAndCompute(reference_gray, None)
    second, second_descriptors = detector.detectAndCompute(current_gray, None)
    if first_descriptors is None or second_descriptors is None:
        return None
    matches = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
        first_descriptors, second_descriptors, k=2
    )
    good = [pair[0] for pair in matches if len(pair) == 2 and pair[0].distance < 0.72 * pair[1].distance]
    if len(good) < 25:
        return None
    source = np.float32([first[item.queryIdx].pt for item in good])
    destination = np.float32([second[item.trainIdx].pt for item in good])
    transform, _ = cv2.estimateAffinePartial2D(
        source, destination, method=cv2.RANSAC, ransacReprojThreshold=2.0
    )
    if transform is None:
        return None
    shift = math.hypot(float(transform[0, 2]), float(transform[1, 2]))
    rotation = math.degrees(math.atan2(float(transform[1, 0]), float(transform[0, 0])))
    return shift, rotation


class Consensus:
    def __init__(self, limits: MonitorConfig):
        self.limits = limits
        self.history: deque[frozenset[str]] = deque(maxlen=limits.confirmations_required)

    def decide(
        self, printing: bool, observations: tuple[CameraObservation, ...]
    ) -> MonitorDecision:
        reasons: list[str] = []
        unstable = tuple(
            item.camera for item in observations if item.camera_stable is False
        )
        failed_quality = tuple(
            item.camera for item in observations if not item.quality_passed
        )
        suspicious = frozenset(
            item.camera
            for item in observations
            if item.quality_passed
            and item.camera_stable is True
            and item.failure_score is not None
            and item.failure_score >= self.limits.pause_score
        )
        warning = tuple(
            item.camera
            for item in observations
            if item.quality_passed
            and item.camera_stable is True
            and item.failure_score is not None
            and self.limits.warning_score <= item.failure_score < self.limits.pause_score
        )
        self.history.append(suspicious if printing else frozenset())
        confirmed = set.intersection(*(set(item) for item in self.history)) if self.history else set()
        enough_history = len(self.history) == self.limits.confirmations_required
        pause = (
            printing
            and enough_history
            and len(confirmed) >= self.limits.cameras_required
        )
        if unstable:
            reasons.append("camera mount moved: " + ", ".join(unstable))
        if failed_quality:
            reasons.append("unusable image: " + ", ".join(failed_quality))
        if suspicious:
            reasons.append("print-failure model: " + ", ".join(sorted(suspicious)))
        elif warning:
            reasons.append("possible print anomaly: " + ", ".join(sorted(warning)))
        severity = "pause" if pause else "warning" if reasons else "normal"
        return MonitorDecision(
            printing, severity, pause, tuple(sorted(confirmed)), len(self.history), tuple(reasons)
        )


def _require_vision() -> None:
    if cv2 is None or np is None:
        raise RuntimeError("OpenCV and NumPy are required for camera monitoring")


class PrintMonitor:
    def __init__(self, config: AppConfig, client: OctoPrintClient):
        _require_vision()
        self.config = config
        self.client = client
        self.consensus = Consensus(config.monitor)
        self.model = FailureModel(config.monitor.model_path) if config.monitor.model_path else None

    def record_reference(self, frames: tuple[CapturedFrame, ...] | None = None) -> dict:
        from .capture import capture_set

        frames = frames or capture_set(self.config.cameras, self.config.state_dir / "captures")
        destination = self.config.state_dir / "monitor" / "reference"
        destination.mkdir(parents=True, exist_ok=True)
        paths = {}
        for frame in frames:
            target = destination / f"{frame.camera}.jpg"
            shutil.copy2(frame.path, target)
            paths[frame.camera] = str(target)
        return paths

    def observe_once(self) -> dict:
        from .capture import capture_set

        printer = self.client.state()
        frames = capture_set(self.config.cameras, self.config.state_dir / "captures")
        observations = tuple(self._observe(frame) for frame in frames)
        decision = self.consensus.decide(printer.printing, observations)
        paused = False
        if decision.pause_requested and self.config.monitor.auto_pause:
            # Re-read immediately so a completed or already-paused job is never acted on.
            if self.client.state().printing:
                self.client.pause()
                paused = True
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "printer": asdict(printer),
            "observations": [asdict(item) for item in observations],
            "decision": asdict(decision),
            "octoprint_paused": paused,
            "model_enabled": self.model is not None,
        }
        event_dir = self.config.state_dir / "monitor"
        event_dir.mkdir(parents=True, exist_ok=True)
        with (event_dir / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        return event

    def _observe(self, frame: CapturedFrame) -> CameraObservation:
        from .quality import assess_image

        quality = assess_image(frame.path, self.config.quality)
        image = cv2.imread(str(frame.path))
        reference_path = self.config.state_dir / "monitor" / "reference" / f"{frame.camera}.jpg"
        movement = None
        if reference_path.exists() and image is not None:
            reference = cv2.imread(str(reference_path))
            if reference is not None:
                movement = camera_motion(reference, image)
        shift, rotation, stable = None, None, None
        if movement is not None:
            shift, rotation = movement
            stable = (
                shift <= self.config.monitor.maximum_camera_shift_px
                and abs(rotation) <= self.config.monitor.maximum_camera_rotation_deg
            )
        score = self.model.score(image) if self.model and image is not None and quality.passed else None
        return CameraObservation(
            frame.camera, str(frame.path), quality.passed, score, shift, rotation, stable
        )

    def watch(self) -> None:
        while True:
            printer = self.client.state()
            if printer.printing:
                event = self.observe_once()
            else:
                # Poll OctoPrint cheaply while idle; camera capture and inference
                # start automatically with the next print.
                event = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "printer": asdict(printer),
                    "decision": {"severity": "idle", "pause_requested": False},
                    "model_enabled": self.model is not None,
                }
            print(json.dumps(event), flush=True)
            time.sleep(self.config.monitor.interval_seconds)
