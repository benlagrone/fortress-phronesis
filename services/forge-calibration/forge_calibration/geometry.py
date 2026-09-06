from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class Checkerboard:
    inner_columns: int = 8
    inner_rows: int = 5
    square_mm: float = 22.0

    @property
    def pattern_size(self) -> tuple[int, int]:
        return self.inner_columns, self.inner_rows

    def object_points(self) -> np.ndarray:
        points = np.zeros((self.inner_rows * self.inner_columns, 3), np.float32)
        points[:, :2] = (
            np.mgrid[0 : self.inner_columns, 0 : self.inner_rows].T.reshape(-1, 2)
            * self.square_mm
        )
        return points


@dataclass
class CameraModel:
    matrix: np.ndarray
    distortion: np.ndarray
    image_size: tuple[int, int]
    rms_px: float


@dataclass
class BedPose:
    rotation: np.ndarray
    translation: np.ndarray
    reprojection_rms_px: float

    def projection(self, camera: CameraModel) -> np.ndarray:
        return camera.matrix @ np.hstack((self.rotation, self.translation.reshape(3, 1)))


@dataclass(frozen=True)
class PartialCheckerboard:
    """A visible rectangular subset of a larger checkerboard.

    The grid size is measured in detected inner corners. Its absolute location
    on the full checkerboard is intentionally not inferred: an unmarked
    checkerboard is periodic, so a partial view has more than one valid origin.
    """

    corners: np.ndarray
    columns: int
    rows: int


def find_checkerboard(image: np.ndarray, board: Checkerboard) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCornersSB(
        gray,
        board.pattern_size,
        flags=cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY,
    )
    if not found:
        raise ValueError("known-size checkerboard was not detected")
    return corners.astype(np.float32)


def find_partial_checkerboard(
    image: np.ndarray,
    board: Checkerboard,
    minimum_columns: int = 3,
    minimum_rows: int = 3,
) -> PartialCheckerboard:
    """Find the largest visible checkerboard rectangle without inventing an origin."""
    if minimum_columns < 3 or minimum_rows < 3:
        raise ValueError("partial checkerboard minimum must be at least 3x3 corners")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_LARGER
    best: PartialCheckerboard | None = None
    for rows in range(board.inner_rows, minimum_rows - 1, -1):
        for columns in range(board.inner_columns, minimum_columns - 1, -1):
            found, corners, meta = cv2.findChessboardCornersSBWithMeta(
                gray, (columns, rows), flags=flags
            )
            if not found or corners is None or meta is None:
                continue
            detected_rows, detected_columns = meta.shape[:2]
            if detected_columns > board.inner_columns or detected_rows > board.inner_rows:
                continue
            candidate = PartialCheckerboard(
                corners.astype(np.float32), detected_columns, detected_rows
            )
            if best is None or len(candidate.corners) > len(best.corners):
                best = candidate
    if best is None:
        raise ValueError("no 3x3 or larger checkerboard subset was detected")
    return best


def calibrate_intrinsics(
    images: Iterable[np.ndarray], board: Checkerboard
) -> CameraModel:
    object_sets: list[np.ndarray] = []
    image_sets: list[np.ndarray] = []
    image_size: tuple[int, int] | None = None
    for image in images:
        height, width = image.shape[:2]
        if image_size and image_size != (width, height):
            raise ValueError("all calibration images must have the same dimensions")
        image_size = (width, height)
        image_sets.append(find_checkerboard(image, board))
        object_sets.append(board.object_points())
    if len(image_sets) < 10:
        raise ValueError("at least 10 distinct checkerboard views are required")
    assert image_size is not None
    rms, matrix, distortion, _, _ = cv2.calibrateCamera(
        object_sets, image_sets, image_size, None, None
    )
    return CameraModel(matrix, distortion, image_size, float(rms))


def solve_bed_pose(
    image: np.ndarray, board: Checkerboard, camera: CameraModel
) -> BedPose:
    corners = find_checkerboard(image, board)
    ok, rotation_vector, translation = cv2.solvePnP(
        board.object_points(), corners, camera.matrix, camera.distortion
    )
    if not ok:
        raise ValueError("could not solve the camera-to-bed pose")
    rotation, _ = cv2.Rodrigues(rotation_vector)
    projected, _ = cv2.projectPoints(
        board.object_points(), rotation_vector, translation, camera.matrix, camera.distortion
    )
    residual = projected.reshape(-1, 2) - corners.reshape(-1, 2)
    rms = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return BedPose(rotation, translation.reshape(3), rms)


def detect_marker_center(
    image: np.ndarray, marker_id: int = 23
) -> tuple[float, float]:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(image)
    if ids is None:
        raise ValueError("toolhead marker was not detected")
    matches = np.flatnonzero(ids.reshape(-1) == marker_id)
    if len(matches) != 1:
        raise ValueError(f"expected one toolhead marker {marker_id}, found {len(matches)}")
    center = corners[int(matches[0])].reshape(4, 2).mean(axis=0)
    return float(center[0]), float(center[1])


def triangulate_bed_point(
    pixels: tuple[tuple[float, float], ...],
    cameras: tuple[CameraModel, ...],
    poses: tuple[BedPose, ...],
) -> tuple[np.ndarray, float]:
    """Triangulate in bed coordinates using all available camera observations.

    More than two observations create an overdetermined DLT system. A bad view
    cannot silently pass because the maximum reprojection error is returned.
    """
    if not (len(pixels) == len(cameras) == len(poses)) or len(pixels) < 2:
        raise ValueError("two or more matching pixels, cameras, and poses are required")
    rows: list[np.ndarray] = []
    for pixel, camera, pose in zip(pixels, cameras, poses):
        point = np.asarray(pixel, dtype=np.float64).reshape(1, 1, 2)
        x, y = cv2.undistortPoints(point, camera.matrix, camera.distortion).reshape(2)
        projection = np.hstack((pose.rotation, pose.translation.reshape(3, 1)))
        rows.extend((x * projection[2] - projection[0], y * projection[2] - projection[1]))
    _, _, vh = np.linalg.svd(np.asarray(rows))
    homogeneous = vh[-1]
    if abs(homogeneous[3]) < 1e-12:
        raise ValueError("camera rays do not form a stable 3D intersection")
    point = homogeneous[:3] / homogeneous[3]
    errors: list[float] = []
    for pixel, camera, pose in zip(pixels, cameras, poses):
        rotation_vector, _ = cv2.Rodrigues(pose.rotation)
        projected, _ = cv2.projectPoints(
            point.reshape(1, 3),
            rotation_vector,
            pose.translation,
            camera.matrix,
            camera.distortion,
        )
        projected = projected.reshape(2)
        errors.append(float(np.linalg.norm(projected - np.asarray(pixel))))
    return point, float(max(errors))


def save_camera_model(path: Path, model: CameraModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        matrix=model.matrix,
        distortion=model.distortion,
        image_size=np.asarray(model.image_size),
        rms_px=np.asarray(model.rms_px),
    )


def load_camera_model(path: Path) -> CameraModel:
    with np.load(path) as data:
        return CameraModel(
            data["matrix"],
            data["distortion"],
            tuple(int(value) for value in data["image_size"]),
            float(data["rms_px"]),
        )


def save_bed_pose(path: Path, pose: BedPose) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        rotation=pose.rotation,
        translation=pose.translation,
        reprojection_rms_px=np.asarray(pose.reprojection_rms_px),
    )


def load_bed_pose(path: Path) -> BedPose:
    with np.load(path) as data:
        return BedPose(
            data["rotation"],
            data["translation"],
            float(data["reprojection_rms_px"]),
        )
