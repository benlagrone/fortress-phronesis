from __future__ import annotations

import json
from pathlib import Path
from time import sleep

import cv2
import numpy as np

from .capture import capture_set
from .config import AppConfig
from .geometry import (
    calibrate_projective_camera,
    detect_marker_center,
    save_projective_camera,
    triangulate_projective_point,
)
from .octoprint import OctoPrintClient
from .quality import assess_image


def collect_observations(
    config: AppConfig,
    output: Path,
    x_values: tuple[float, ...],
    y_values: tuple[float, ...],
    z_values: tuple[float, ...],
    settle_seconds: float,
) -> dict:
    client = OctoPrintClient.from_config_file(
        config.octoprint_url, config.octoprint_api_key_file
    )
    state = client.state()
    if not state.operational or state.printing:
        raise ValueError("printer must be operational and idle")
    if state.hotend_target_c or state.bed_target_c:
        raise ValueError("heater targets must be zero during geometric calibration")
    if state.hotend_actual_c > config.safety.maximum_hotend_c:
        raise ValueError("hotend is too warm for geometric calibration")
    if state.bed_actual_c > config.safety.maximum_bed_c:
        raise ValueError("bed is too warm for geometric calibration")

    capture_dir = output.parent / f"{output.stem}-frames"
    observations = []
    client.commands(["G90", "G28", "G1 Z60 F1200", "M400"])
    sleep(35.0)
    try:
        for z in z_values:
            for y in y_values:
                for x in x_values:
                    client.commands(
                        [f"G1 Z{z:.3f} F1200", f"G1 X{x:.3f} Y{y:.3f} F3000", "M400"]
                    )
                    sleep(settle_seconds)
                    frames = capture_set(config.cameras, capture_dir)
                    pixels = {}
                    paths = {}
                    for frame in frames:
                        paths[frame.camera] = str(frame.path)
                        quality = assess_image(frame.path, config.quality)
                        if not quality.passed:
                            continue
                        image = cv2.imread(str(frame.path))
                        try:
                            pixels[frame.camera] = list(detect_marker_center(image))
                        except ValueError:
                            continue
                    observations.append(
                        {
                            "nozzle_xyz_mm": [x, y, z],
                            "pixels": pixels,
                            "frames": paths,
                        }
                    )
                    print(
                        json.dumps(
                            {"xyz_mm": [x, y, z], "visible_cameras": sorted(pixels)}
                        ),
                        flush=True,
                    )
    finally:
        client.commands(["G90", "G1 Z100 F1200", "G1 X150 Y150 F3000", "M400"])
    payload = {"marker_id": 23, "observations": observations}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    return payload


def calibrate_observations(config: AppConfig, source: Path) -> dict:
    payload = json.loads(source.read_text())
    observations = payload["observations"]
    models = {}
    validation_models = {}
    validation_indexes = {index for index in range(len(observations)) if index % 5 == 2}
    for camera in config.cameras:
        usable = [item for item in observations if camera.name in item["pixels"]]
        if len(usable) < 8:
            continue
        points = np.asarray([item["nozzle_xyz_mm"] for item in usable], dtype=np.float64)
        pixels = np.asarray([item["pixels"][camera.name] for item in usable], dtype=np.float64)
        model = calibrate_projective_camera(points, pixels)
        models[camera.name] = model

        training = [
            item
            for index, item in enumerate(observations)
            if index not in validation_indexes and camera.name in item["pixels"]
        ]
        training_points = np.asarray(
            [item["nozzle_xyz_mm"] for item in training], dtype=np.float64
        )
        training_pixels = np.asarray(
            [item["pixels"][camera.name] for item in training], dtype=np.float64
        )
        validation_models[camera.name] = calibrate_projective_camera(
            training_points, training_pixels
        )

    if len(models) < 2:
        raise ValueError("at least two cameras need eight or more marker observations")
    bad_pixels = {
        name: model.rms_px
        for name, model in models.items()
        if model.rms_px > config.quality.maximum_reprojection_error_px
    }
    if bad_pixels:
        detail = ", ".join(f"{name}={error:.3f}px" for name, error in bad_pixels.items())
        raise ValueError(f"projective calibration rejected: excessive fit error: {detail}")

    validation_errors = []
    for index, item in enumerate(observations):
        if index not in validation_indexes:
            continue
        names = [name for name in validation_models if name in item["pixels"]]
        if len(names) < 2:
            continue
        measured, reprojection = triangulate_projective_point(
            tuple(tuple(item["pixels"][name]) for name in names),
            tuple(validation_models[name] for name in names),
        )
        expected = np.asarray(item["nozzle_xyz_mm"])
        validation_errors.append(
            {
                "expected_xyz_mm": expected.tolist(),
                "measured_xyz_mm": measured.tolist(),
                "error_mm": float(np.linalg.norm(measured - expected)),
                "reprojection_error_px": reprojection,
                "cameras": names,
            }
        )
    if not validation_errors:
        raise ValueError("fewer than two cameras overlap at every calibration position")
    errors = np.asarray([item["error_mm"] for item in validation_errors])
    rms_mm = float(np.sqrt(np.mean(errors**2)))
    maximum_error_mm = float(np.max(errors))
    if rms_mm > 0.25 or maximum_error_mm > 0.50:
        raise ValueError(
            "projective calibration rejected: held-out error "
            f"rms={rms_mm:.3f}mm maximum={maximum_error_mm:.3f}mm"
        )
    for name, model in models.items():
        save_projective_camera(
            config.state_dir / "models" / f"{name}-projective.npz", model
        )
    return {
        "cameras": {
            name: {"observations": model.observations, "rms_px": model.rms_px}
            for name, model in models.items()
        },
        "validation_positions": len(validation_errors),
        "validation_method": "deterministic held-out positions",
        "rms_mm": rms_mm,
        "maximum_error_mm": maximum_error_mm,
    }
