from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


MAXIMUM_BED_SLINGER_AGREEMENT_MM = 0.50


def fuse_bed_slinger_predictions(
    primary_predictions: list[np.ndarray],
    verifier_predictions: list[np.ndarray],
    maximum_agreement_mm: float = MAXIMUM_BED_SLINGER_AGREEMENT_MM,
) -> tuple[np.ndarray, float]:
    if not primary_predictions:
        raise ValueError("precision refused: no paired-marker bed-slinger view")
    if not verifier_predictions:
        raise ValueError("precision refused: no independent toolhead verification view")
    nozzle = np.mean(np.asarray(primary_predictions), axis=0)
    verifier_xz = np.mean(np.asarray(verifier_predictions), axis=0)
    agreement = float(np.linalg.norm(nozzle[[0, 2]] - verifier_xz))
    if agreement > maximum_agreement_mm:
        raise ValueError(
            f"precision refused: independent cameras disagree by {agreement:.3f}mm; "
            f"limit is {maximum_agreement_mm:.3f}mm"
        )
    return nozzle, agreement


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


@dataclass
class ToolheadPlaneCamera:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    coefficients: np.ndarray
    rms_mm: float
    maximum_error_mm: float
    observations: int

    def predict_xz(self, toolhead_pixel: tuple[float, float]) -> np.ndarray:
        raw = np.asarray(toolhead_pixel, dtype=np.float64)
        normalized = (raw - self.feature_mean) / self.feature_scale
        return _plane_features(normalized.reshape(1, 2))[0] @ self.coefficients


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


def _plane_features(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise ValueError("toolhead marker features must be Nx2")
    u = values[:, 0]
    v = values[:, 1]
    return np.column_stack((np.ones(len(values)), u, v, u * u, u * v, v * v))


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


def calibrate_toolhead_plane_camera(
    toolhead_pixels: np.ndarray,
    nozzle_xz_mm: np.ndarray,
) -> ToolheadPlaneCamera:
    raw = np.asarray(toolhead_pixels, dtype=np.float64)
    expected = np.asarray(nozzle_xz_mm, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[1] != 2 or expected.shape != (len(raw), 2):
        raise ValueError("expected matching Nx2 marker pixels and Nx2 nozzle XZ positions")
    if len(raw) < 8:
        raise ValueError("at least eight toolhead observations are required")
    if np.linalg.matrix_rank(expected - expected.mean(axis=0)) < 2:
        raise ValueError("toolhead positions must span X and Z")
    mean = raw.mean(axis=0)
    scale = raw.std(axis=0)
    if np.any(scale < 1e-6):
        raise ValueError("toolhead observations do not vary on both image axes")
    design = _plane_features((raw - mean) / scale)
    coefficients, _, _, _ = np.linalg.lstsq(design, expected, rcond=None)
    predicted = design @ coefficients
    errors = np.linalg.norm(predicted - expected, axis=1)
    return ToolheadPlaneCamera(
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


def save_toolhead_plane_camera(path: Path, model: ToolheadPlaneCamera) -> None:
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


def load_toolhead_plane_camera(path: Path) -> ToolheadPlaneCamera:
    with np.load(path) as data:
        return ToolheadPlaneCamera(
            data["feature_mean"],
            data["feature_scale"],
            data["coefficients"],
            float(data["rms_mm"]),
            float(data["maximum_error_mm"]),
            int(data["observations"]),
        )
