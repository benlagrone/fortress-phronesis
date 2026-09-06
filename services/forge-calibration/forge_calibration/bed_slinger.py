from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class BedSlingerCamera:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    coefficients: np.ndarray
    rms_mm: float
    maximum_error_mm: float
    observations: int

    def predict(
        self,
        toolhead_pixel: tuple[float, float],
        bed_pixel: tuple[float, float],
    ) -> np.ndarray:
        raw = np.asarray((*toolhead_pixel, *bed_pixel), dtype=np.float64)
        normalized = (raw - self.feature_mean) / self.feature_scale
        return _polynomial_features(normalized.reshape(1, 4))[0] @ self.coefficients


def _polynomial_features(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("paired marker features must be Nx4")
    columns = [np.ones(len(values))]
    columns.extend(values[:, index] for index in range(4))
    for left in range(4):
        for right in range(left, 4):
            columns.append(values[:, left] * values[:, right])
    return np.column_stack(columns)


def calibrate_bed_slinger_camera(
    paired_pixels: np.ndarray,
    nozzle_xyz_mm: np.ndarray,
) -> BedSlingerCamera:
    raw = np.asarray(paired_pixels, dtype=np.float64)
    expected = np.asarray(nozzle_xyz_mm, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[1] != 4 or expected.shape != (len(raw), 3):
        raise ValueError("expected matching Nx4 marker pixels and Nx3 nozzle positions")
    if len(raw) < 20:
        raise ValueError("at least 20 paired-marker observations are required")
    if np.linalg.matrix_rank(expected - expected.mean(axis=0)) < 3:
        raise ValueError("calibration positions must span X, Y, and Z")
    mean = raw.mean(axis=0)
    scale = raw.std(axis=0)
    if np.any(scale < 1e-6):
        raise ValueError("paired marker observations do not vary on every image axis")
    design = _polynomial_features((raw - mean) / scale)
    coefficients, _, _, _ = np.linalg.lstsq(design, expected, rcond=None)
    predicted = design @ coefficients
    errors = np.linalg.norm(predicted - expected, axis=1)
    return BedSlingerCamera(
        mean,
        scale,
        coefficients,
        float(np.sqrt(np.mean(errors**2))),
        float(np.max(errors)),
        len(raw),
    )


def save_bed_slinger_camera(path: Path, model: BedSlingerCamera) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        feature_mean=model.feature_mean,
        feature_scale=model.feature_scale,
        coefficients=model.coefficients,
        rms_mm=np.asarray(model.rms_mm),
        maximum_error_mm=np.asarray(model.maximum_error_mm),
        observations=np.asarray(model.observations),
    )


def load_bed_slinger_camera(path: Path) -> BedSlingerCamera:
    with np.load(path) as data:
        return BedSlingerCamera(
            data["feature_mean"],
            data["feature_scale"],
            data["coefficients"],
            float(data["rms_mm"]),
            float(data["maximum_error_mm"]),
            int(data["observations"]),
        )
