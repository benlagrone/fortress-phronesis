from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class TouchOff:
    marker_to_nozzle_x_mm: float
    marker_to_nozzle_y_mm: float
    marker_to_nozzle_z_mm: float
    gauge_thickness_mm: float
    created_at: str

    @classmethod
    def create(
        cls, marker_xyz_mm: tuple[float, float, float], nozzle_xyz_mm: tuple[float, float, float], gauge_mm: float
    ) -> "TouchOff":
        return cls(
            nozzle_xyz_mm[0] - marker_xyz_mm[0],
            nozzle_xyz_mm[1] - marker_xyz_mm[1],
            nozzle_xyz_mm[2] - marker_xyz_mm[2],
            gauge_mm,
            datetime.now(timezone.utc).isoformat(),
        )

    def nozzle_xyz(self, marker_xyz_mm: tuple[float, float, float]) -> tuple[float, float, float]:
        return (
            marker_xyz_mm[0] + self.marker_to_nozzle_x_mm,
            marker_xyz_mm[1] + self.marker_to_nozzle_y_mm,
            marker_xyz_mm[2] + self.marker_to_nozzle_z_mm,
        )


def save_touch_off(path: Path, touch_off: TouchOff) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(touch_off), indent=2) + "\n")
    temporary.replace(path)


def load_touch_off(path: Path) -> TouchOff:
    return TouchOff(**json.loads(path.read_text()))
