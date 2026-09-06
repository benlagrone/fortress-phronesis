from __future__ import annotations

import json
from pathlib import Path
from time import sleep

import cv2
import numpy as np

from .bed_slinger import (
    calibrate_bed_slinger_camera,
    calibrate_toolhead_plane_camera,
    save_bed_slinger_camera,
    save_toolhead_plane_camera,
)
from .capture import capture_set
from .config import AppConfig
from .geometry import detect_marker_centers
from .octoprint import OctoPrintClient
from .quality import assess_image


def collect_bed_slinger_observations(
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
    if min(z_values) < 5.0 or max(z_values) > 40.0:
        raise ValueError("bed-slinger calibration Z values must stay between 5 and 40 mm")

    capture_dir = output.parent / f"{output.stem}-frames"
    observations = []
    client.commands(["G90", "G28", "G1 Z10 F600", "M400"])
    sleep(35.0)
    try:
        for z in z_values:
            for y in y_values:
                for x in x_values:
                    client.commands(
                        [f"G1 Z{z:.3f} F600", f"G1 X{x:.3f} Y{y:.3f} F2400", "M400"]
                    )
                    sleep(settle_seconds)
                    frames = capture_set(config.cameras, capture_dir)
                    paired = {}
                    marker_tracks = {}
                    paths = {}
                    for frame in frames:
                        paths[frame.camera] = str(frame.path)
                        if not assess_image(frame.path, config.quality).passed:
                            continue
                        markers = detect_marker_centers(cv2.imread(str(frame.path)))
                        marker_tracks[frame.camera] = {
                            str(marker_id): list(pixel)
                            for marker_id, pixel in markers.items()
                        }
                        if 23 in markers and 24 in markers:
                            paired[frame.camera] = {
                                "toolhead": list(markers[23]),
                                "bed": list(markers[24]),
                            }
                    observations.append(
                        {
                            "nozzle_xyz_mm": [x, y, z],
                            "markers": marker_tracks,
                            "paired_markers": paired,
                            "frames": paths,
                        }
                    )
                    print(
                        json.dumps(
                            {"xyz_mm": [x, y, z], "paired_cameras": sorted(paired)}
                        ),
                        flush=True,
                    )
    finally:
        client.commands(["G90", "G1 Z40 F600", "G1 X150 Y150 F2400", "M400"])
    payload = {"toolhead_marker_id": 23, "bed_marker_id": 24, "observations": observations}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2))
    return payload


def calibrate_bed_slinger_observations(config: AppConfig, source: Path) -> dict:
    observations = json.loads(source.read_text())["observations"]
    holdout = {index for index in range(len(observations)) if index % 5 == 2}
    primary_models = {}
    primary_validation = {}
    verifier_models = {}
    verifier_validation = {}
    for camera in config.cameras:
        usable = [item for item in observations if camera.name in item["paired_markers"]]
        if len(usable) < 20:
            continue

        def arrays(items):
            pixels = []
            points = []
            for item in items:
                pair = item["paired_markers"][camera.name]
                pixels.append((*pair["toolhead"], *pair["bed"]))
                points.append(item["nozzle_xyz_mm"])
            return np.asarray(pixels), np.asarray(points)

        pixels, points = arrays(usable)
        primary_models[camera.name] = calibrate_bed_slinger_camera(pixels, points)
        training = [
            item
            for index, item in enumerate(observations)
            if index not in holdout and camera.name in item["paired_markers"]
        ]
        training_pixels, training_points = arrays(training)
        primary_validation[camera.name] = calibrate_bed_slinger_camera(
            training_pixels, training_points
        )

    primary_names = set(primary_models)
    for camera in config.cameras:
        if camera.name in primary_names:
            continue
        usable = [
            item
            for item in observations
            if "23" in item.get("markers", {}).get(camera.name, {})
        ]
        if len(usable) < 20:
            continue

        def head_arrays(items):
            pixels = [item["markers"][camera.name]["23"] for item in items]
            points = [
                (item["nozzle_xyz_mm"][0], item["nozzle_xyz_mm"][2]) for item in items
            ]
            return np.asarray(pixels), np.asarray(points)

        pixels, points = head_arrays(usable)
        verifier_models[camera.name] = calibrate_toolhead_plane_camera(pixels, points)
        training = [
            item
            for index, item in enumerate(observations)
            if index not in holdout
            and "23" in item.get("markers", {}).get(camera.name, {})
        ]
        training_pixels, training_points = head_arrays(training)
        verifier_validation[camera.name] = calibrate_toolhead_plane_camera(
            training_pixels, training_points
        )
    if not primary_models:
        raise ValueError("one camera needs 20 observations containing both markers")
    if not verifier_models:
        raise ValueError("a second camera needs 20 toolhead-marker observations")

    validation_errors = []
    verifier_errors = []
    agreement_errors = []
    for index, item in enumerate(observations):
        if index not in holdout:
            continue
        primary_predictions = []
        for name, model in primary_validation.items():
            pair = item["paired_markers"].get(name)
            if pair is None:
                continue
            primary_predictions.append(
                model.predict(tuple(pair["toolhead"]), tuple(pair["bed"]))
            )
        verifier_predictions = []
        for name, model in verifier_validation.items():
            pixel = item.get("markers", {}).get(name, {}).get("23")
            if pixel is not None:
                verifier_predictions.append(model.predict_xz(tuple(pixel)))
        if not primary_predictions or not verifier_predictions:
            continue
        measured = np.mean(primary_predictions, axis=0)
        measured_xz = np.mean(verifier_predictions, axis=0)
        expected = np.asarray(item["nozzle_xyz_mm"])
        validation_errors.append(float(np.linalg.norm(measured - expected)))
        verifier_errors.append(float(np.linalg.norm(measured_xz - expected[[0, 2]])))
        agreement_errors.append(float(np.linalg.norm(measured[[0, 2]] - measured_xz)))
    if not validation_errors:
        raise ValueError("no held-out position has two paired-marker camera observations")
    errors = np.asarray(validation_errors)
    verifier = np.asarray(verifier_errors)
    agreement = np.asarray(agreement_errors)
    rms = float(np.sqrt(np.mean(errors**2)))
    maximum = float(np.max(errors))
    verifier_rms = float(np.sqrt(np.mean(verifier**2)))
    verifier_maximum = float(np.max(verifier))
    agreement_maximum = float(np.max(agreement))
    if (
        rms > 0.25
        or maximum > 0.50
        or verifier_rms > 0.25
        or verifier_maximum > 0.50
        or agreement_maximum > 0.50
    ):
        raise ValueError(
            "bed-slinger calibration rejected: "
            f"primary rms={rms:.3f}mm maximum={maximum:.3f}mm; "
            f"verifier rms={verifier_rms:.3f}mm maximum={verifier_maximum:.3f}mm; "
            f"camera agreement maximum={agreement_maximum:.3f}mm"
        )
    for name, model in primary_models.items():
        save_bed_slinger_camera(
            config.state_dir / "models" / f"{name}-bed-slinger.npz", model
        )
    for name, model in verifier_models.items():
        save_toolhead_plane_camera(
            config.state_dir / "models" / f"{name}-toolhead-plane.npz", model
        )
    return {
        "primary_cameras": {
            name: {
                "observations": model.observations,
                "fit_rms_mm": model.rms_mm,
                "fit_maximum_error_mm": model.maximum_error_mm,
            }
            for name, model in primary_models.items()
        },
        "verifier_cameras": {
            name: {
                "observations": model.observations,
                "fit_rms_mm": model.rms_mm,
                "fit_maximum_error_mm": model.maximum_error_mm,
            }
            for name, model in verifier_models.items()
        },
        "held_out_positions": len(errors),
        "held_out_rms_mm": rms,
        "held_out_maximum_error_mm": maximum,
        "verifier_held_out_rms_mm": verifier_rms,
        "verifier_held_out_maximum_error_mm": verifier_maximum,
        "camera_agreement_maximum_mm": agreement_maximum,
    }
