from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2

from .config import QualityConfig


@dataclass(frozen=True)
class ImageQuality:
    focus_score: float
    mean_luma: float
    width: int
    height: int
    passed: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict:
        result = asdict(self)
        result["failures"] = list(self.failures)
        return result


def assess_image(path: str | Path, limits: QualityConfig) -> ImageQuality:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"unable to decode image: {path}")
    focus = float(cv2.Laplacian(image, cv2.CV_64F).var())
    luma = float(image.mean())
    failures: list[str] = []
    if focus < limits.minimum_focus_score:
        failures.append("image is too soft for precision measurement")
    if luma < limits.minimum_mean_luma:
        failures.append("image is underexposed")
    if luma > limits.maximum_mean_luma:
        failures.append("image is overexposed")
    height, width = image.shape[:2]
    if width < 1280 or height < 720:
        failures.append("capture resolution is below 1280x720")
    return ImageQuality(focus, luma, width, height, not failures, tuple(failures))
