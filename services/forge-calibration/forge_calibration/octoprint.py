from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

from .config import SafetyConfig


@dataclass(frozen=True)
class PrinterState:
    operational: bool
    printing: bool
    hotend_actual_c: float
    hotend_target_c: float
    bed_actual_c: float
    bed_target_c: float


class OctoPrintClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": api_key})

    @classmethod
    def from_config_file(cls, base_url: str, path: Path) -> "OctoPrintClient":
        raw = yaml.safe_load(path.read_text())
        return cls(base_url, raw["api"]["key"])

    def _get(self, route: str) -> dict[str, Any]:
        response = self.session.get(self.base_url + route, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, route: str, payload: dict[str, Any]) -> None:
        response = self.session.post(
            self.base_url + route, json=payload, timeout=self.timeout
        )
        response.raise_for_status()

    def state(self) -> PrinterState:
        payload = self._get("/api/printer")
        flags = payload["state"]["flags"]
        tool = payload["temperature"]["tool0"]
        bed = payload["temperature"]["bed"]
        return PrinterState(
            operational=bool(flags.get("operational")),
            printing=bool(flags.get("printing")),
            hotend_actual_c=float(tool["actual"]),
            hotend_target_c=float(tool["target"]),
            bed_actual_c=float(bed["actual"]),
            bed_target_c=float(bed["target"]),
        )

    def commands(self, commands: list[str]) -> None:
        self._post("/api/printer/command", {"commands": commands})

    def job(self) -> dict[str, Any]:
        return self._get("/api/job")

    def pause(self) -> None:
        self._post("/api/job", {"command": "pause", "action": "pause"})


def validate_guarded_z_step(
    state: PrinterState,
    current_z_mm: float,
    delta_mm: float,
    safety: SafetyConfig,
    allow_below_zero: bool,
) -> float:
    if not state.operational or state.printing:
        raise ValueError("printer must be operational and idle")
    if state.hotend_target_c or state.bed_target_c:
        raise ValueError("heater targets must be zero during geometric calibration")
    if state.hotend_actual_c > safety.maximum_hotend_c:
        raise ValueError("hotend is too warm for geometric calibration")
    if state.bed_actual_c > safety.maximum_bed_c:
        raise ValueError("bed is too warm for geometric calibration")
    if abs(delta_mm) > safety.max_step_mm:
        raise ValueError(f"Z step exceeds {safety.max_step_mm:.3f} mm guard")
    destination = current_z_mm + delta_mm
    if destination < 0 and not allow_below_zero:
        raise ValueError("below-zero movement requires an explicit one-step override")
    if destination < safety.minimum_z_mm or destination > safety.maximum_z_mm:
        raise ValueError("requested Z destination is outside configured limits")
    return destination


def guarded_z_commands(delta_mm: float, below_zero: bool) -> list[str]:
    commands = []
    if below_zero:
        commands.append("M211 S0")
    commands.extend(["G91", f"G1 Z{delta_mm:.3f} F60", "G90"])
    if below_zero:
        commands.append("M211 S1")
    commands.extend(["M400", "M114"])
    return commands
