from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CameraConfig:
    name: str
    device: str
    width: int = 1920
    height: int = 1080
    fps: int = 15


@dataclass(frozen=True)
class SafetyConfig:
    max_step_mm: float = 1.0
    minimum_z_mm: float = -2.0
    maximum_z_mm: float = 400.0
    maximum_hotend_c: float = 50.0
    maximum_bed_c: float = 50.0


@dataclass(frozen=True)
class QualityConfig:
    minimum_focus_score: float = 75.0
    minimum_mean_luma: float = 35.0
    maximum_mean_luma: float = 220.0
    maximum_intrinsic_rms_px: float = 0.45
    maximum_stereo_rms_px: float = 0.55
    maximum_reprojection_error_px: float = 0.75


@dataclass(frozen=True)
class MonitorConfig:
    interval_seconds: float = 8.0
    model_path: Path | None = None
    warning_score: float = 0.35
    pause_score: float = 0.70
    confirmations_required: int = 3
    cameras_required: int = 2
    maximum_camera_shift_px: float = 2.0
    maximum_camera_rotation_deg: float = 0.10
    auto_pause: bool = True


@dataclass(frozen=True)
class AppConfig:
    cameras: tuple[CameraConfig, ...]
    state_dir: Path
    octoprint_url: str = "http://127.0.0.1:5000"
    octoprint_api_key_file: Path = Path("/home/benlagrone/.octoprint/config.yaml")
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)


def _values(cls: type, data: dict[str, Any] | None) -> Any:
    return cls(**(data or {}))


def load_config(path: str | Path) -> AppConfig:
    source = Path(path)
    raw = yaml.safe_load(source.read_text()) or {}
    cameras = tuple(CameraConfig(**item) for item in raw["cameras"])
    if len(cameras) < 2:
        raise ValueError("at least two cameras are required for 3D measurement")
    state_dir = Path(raw.get("state_dir", "/var/lib/forge-calibration"))
    monitor_raw = dict(raw.get("monitor") or {})
    if monitor_raw.get("model_path"):
        monitor_raw["model_path"] = Path(monitor_raw["model_path"])
    elif (state_dir / "models" / "print-failure.onnx").exists():
        monitor_raw["model_path"] = state_dir / "models" / "print-failure.onnx"
    return AppConfig(
        cameras=cameras,
        state_dir=state_dir,
        octoprint_url=raw.get("octoprint_url", "http://127.0.0.1:5000"),
        octoprint_api_key_file=Path(
            raw.get("octoprint_api_key_file", "/home/benlagrone/.octoprint/config.yaml")
        ),
        safety=_values(SafetyConfig, raw.get("safety")),
        quality=_values(QualityConfig, raw.get("quality")),
        monitor=_values(MonitorConfig, monitor_raw),
    )
