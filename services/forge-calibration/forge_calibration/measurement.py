from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .bed_slinger import (
    fuse_bed_slinger_predictions,
    load_bed_slinger_camera,
    load_toolhead_plane_camera,
)
from .config import AppConfig
from .geometry import (
    detect_marker_center,
    detect_marker_centers,
    load_bed_pose,
    load_camera_model,
    load_projective_camera,
    triangulate_bed_point,
    triangulate_projective_point,
)
from .quality import assess_image


def measure_bed_slinger_nozzle(
    config: AppConfig, images: dict[str, Path]
) -> tuple[tuple[float, float, float], float, list[str], list[str]]:
    primary_predictions: list[np.ndarray] = []
    verifier_predictions: list[np.ndarray] = []
    primary_visible: list[str] = []
    verifier_visible: list[str] = []
    failures: list[str] = []
    for camera in config.cameras:
        primary_path = config.state_dir / "models" / f"{camera.name}-bed-slinger.npz"
        verifier_path = config.state_dir / "models" / f"{camera.name}-toolhead-plane.npz"
        image_path = images.get(camera.name)
        if image_path is None or not (primary_path.exists() or verifier_path.exists()):
            continue
        quality = assess_image(image_path, config.quality)
        if not quality.passed:
            failures.append(f"{camera.name}: {', '.join(quality.failures)}")
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            failures.append(f"{camera.name}: image cannot be decoded")
            continue
        markers = detect_marker_centers(image)
        if primary_path.exists():
            if 23 not in markers or 24 not in markers:
                failures.append(f"{camera.name}: paired markers 23 and 24 not detected")
                continue
            model = load_bed_slinger_camera(primary_path)
            primary_predictions.append(model.predict(markers[23], markers[24]))
            primary_visible.append(camera.name)
        elif verifier_path.exists():
            if 23 not in markers:
                failures.append(f"{camera.name}: toolhead marker 23 not detected")
                continue
            model = load_toolhead_plane_camera(verifier_path)
            verifier_predictions.append(model.predict_xz(markers[23]))
            verifier_visible.append(camera.name)
    try:
        nozzle, agreement = fuse_bed_slinger_predictions(
            primary_predictions, verifier_predictions
        )
    except ValueError as error:
        detail = "; ".join(failures)
        raise ValueError(f"{error}; {detail}" if detail else str(error)) from error
    return (
        tuple(float(value) for value in nozzle),
        agreement,
        primary_visible,
        verifier_visible,
    )


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


def measure_projective_nozzle(
    config: AppConfig, images: dict[str, Path]
) -> tuple[tuple[float, float, float], float, list[str]]:
    pixels = []
    models = []
    visible = []
    failures = []
    for camera in config.cameras:
        model_path = config.state_dir / "models" / f"{camera.name}-projective.npz"
        image_path = images.get(camera.name)
        if image_path is None or not model_path.exists():
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
            pixels.append(detect_marker_center(image))
        except ValueError as exc:
            failures.append(f"{camera.name}: {exc}")
            continue
        models.append(load_projective_camera(model_path))
        visible.append(camera.name)
    if len(pixels) < 2:
        detail = "; ".join(failures) if failures else "no usable observations"
        raise ValueError(f"precision refused: fewer than two projective views; {detail}")
    point, error = triangulate_projective_point(tuple(pixels), tuple(models))
    if error > config.quality.maximum_reprojection_error_px:
        raise ValueError(
            f"precision refused: reprojection error {error:.3f}px exceeds "
            f"{config.quality.maximum_reprojection_error_px:.3f}px"
        )
    return tuple(float(value) for value in point), error, visible
