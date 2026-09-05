from __future__ import annotations

from pathlib import Path

import cv2

from .config import AppConfig
from .geometry import (
    detect_marker_center,
    load_bed_pose,
    load_camera_model,
    triangulate_bed_point,
)
from .quality import assess_image


def measure_marker(
    config: AppConfig, images: dict[str, Path]
) -> tuple[tuple[float, float, float], float, list[str]]:
    pixels = []
    models = []
    poses = []
    visible = []
    failures = []
    for camera in config.cameras:
        image_path = images.get(camera.name)
        if image_path is None:
            continue
        quality = assess_image(image_path, config.quality)
        if not quality.passed:
            failures.append(f"{camera.name}: {', '.join(quality.failures)}")
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            failures.append(f"{camera.name}: image cannot be decoded")
            continue
        try:
            pixel = detect_marker_center(image)
        except ValueError as exc:
            failures.append(f"{camera.name}: {exc}")
            continue
        pixels.append(pixel)
        models.append(load_camera_model(config.state_dir / "models" / f"{camera.name}-intrinsics.npz"))
        poses.append(load_bed_pose(config.state_dir / "models" / f"{camera.name}-bed-pose.npz"))
        visible.append(camera.name)
    if len(pixels) < 2:
        detail = "; ".join(failures) if failures else "no usable observations"
        raise ValueError(f"precision refused: fewer than two calibrated views; {detail}")
    point, error = triangulate_bed_point(tuple(pixels), tuple(models), tuple(poses))
    if error > config.quality.maximum_reprojection_error_px:
        raise ValueError(
            f"precision refused: reprojection error {error:.3f}px exceeds "
            f"{config.quality.maximum_reprojection_error_px:.3f}px"
        )
    return tuple(float(value) for value in point), error, visible
