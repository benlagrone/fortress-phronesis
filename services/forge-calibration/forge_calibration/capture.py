from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic_ns

import cv2

from .config import CameraConfig


@dataclass(frozen=True)
class CapturedFrame:
    camera: str
    path: Path
    captured_ns: int


def _open(camera: CameraConfig):
    stream = cv2.VideoCapture(camera.device, cv2.CAP_V4L2)
    stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    stream.set(cv2.CAP_PROP_FRAME_WIDTH, camera.width)
    stream.set(cv2.CAP_PROP_FRAME_HEIGHT, camera.height)
    stream.set(cv2.CAP_PROP_FPS, camera.fps)
    if not stream.isOpened():
        raise RuntimeError(f"cannot open camera {camera.name}: {camera.device}")
    return stream


def capture_set(
    cameras: tuple[CameraConfig, ...], output_dir: Path
) -> tuple[CapturedFrame, ...]:
    """Capture two or more cameras concurrently and report acquisition skew."""
    if len(cameras) < 2:
        raise ValueError("at least two cameras are required")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")

    def read(index: int) -> CapturedFrame:
        # Each worker owns one device for its whole lifetime. Opening and camera
        # warm-up happen concurrently, which avoids N-camera startup latency.
        stream = _open(cameras[index])
        try:
            frame = None
            ok = False
            for _ in range(6):
                ok, frame = stream.read()
                if not ok:
                    break
            captured_ns = monotonic_ns()
            if not ok or frame is None:
                raise RuntimeError(f"failed to read camera {cameras[index].name}")
            destination = output_dir / f"{stamp}-{cameras[index].name}.jpg"
            if not cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f"failed to write {destination}")
            return CapturedFrame(cameras[index].name, destination, captured_ns)
        finally:
            stream.release()

    with ThreadPoolExecutor(max_workers=len(cameras)) as pool:
        frames = tuple(pool.map(read, range(len(cameras))))
    return frames


def capture_pair(
    cameras: tuple[CameraConfig, CameraConfig], output_dir: Path
) -> tuple[CapturedFrame, CapturedFrame]:
    frames = capture_set(cameras, output_dir)
    return frames[0], frames[1]


def capture_skew_ms(frames: tuple[CapturedFrame, ...]) -> float:
    times = [frame.captured_ns for frame in frames]
    return (max(times) - min(times)) / 1_000_000
