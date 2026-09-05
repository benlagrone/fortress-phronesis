import sys
from pathlib import Path

import pytest

SERVICE = Path(__file__).parents[1] / "services" / "forge-calibration"
sys.path.insert(0, str(SERVICE))

from forge_calibration.config import SafetyConfig
from forge_calibration.octoprint import (
    PrinterState,
    guarded_z_commands,
    validate_guarded_z_step,
)
from forge_calibration.state import TouchOff


def idle_state(**overrides):
    values = {
        "operational": True,
        "printing": False,
        "hotend_actual_c": 25.0,
        "hotend_target_c": 0.0,
        "bed_actual_c": 25.0,
        "bed_target_c": 0.0,
    }
    values.update(overrides)
    return PrinterState(**values)


def test_guarded_step_accepts_small_cold_idle_move():
    assert validate_guarded_z_step(idle_state(), 3.0, -0.5, SafetyConfig(), False) == 2.5


@pytest.mark.parametrize(
    "state, current, delta, override",
    [
        (idle_state(printing=True), 3.0, -0.1, False),
        (idle_state(hotend_target_c=150.0), 3.0, -0.1, False),
        (idle_state(), 3.0, -1.1, False),
        (idle_state(), 0.0, -0.1, False),
        (idle_state(), -1.9, -0.2, True),
    ],
)
def test_guarded_step_rejects_unsafe_conditions(state, current, delta, override):
    with pytest.raises(ValueError):
        validate_guarded_z_step(state, current, delta, SafetyConfig(), override)


def test_below_zero_commands_restore_soft_endstops():
    commands = guarded_z_commands(-0.1, below_zero=True)
    assert commands[0] == "M211 S0"
    assert commands[-3] == "M211 S1"
    assert commands[-1] == "M114"


def test_touch_off_round_trip():
    touch = TouchOff.create((11.0, 12.0, 20.0), (10.0, 10.0, 0.1), 0.1)
    assert touch.nozzle_xyz((11.0, 12.0, 20.0)) == (10.0, 10.0, pytest.approx(0.1))


def test_three_camera_triangulation_is_metric_and_overdetermined():
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from forge_calibration.geometry import BedPose, CameraModel, triangulate_bed_point

    matrix = np.array([[1000.0, 0.0, 960.0], [0.0, 1000.0, 540.0], [0.0, 0.0, 1.0]])
    camera = CameraModel(matrix, np.zeros(5), (1920, 1080), 0.1)
    poses = (
        BedPose(np.eye(3), np.array([0.0, 0.0, 1000.0]), 0.1),
        BedPose(np.eye(3), np.array([-120.0, 0.0, 1000.0]), 0.1),
        BedPose(np.eye(3), np.array([0.0, -100.0, 1000.0]), 0.1),
    )
    expected = np.array([20.0, 30.0, 10.0])

    def project(pose):
        camera_point = pose.rotation @ expected + pose.translation
        pixel = matrix @ camera_point
        return tuple(pixel[:2] / pixel[2])

    pixels = tuple(project(pose) for pose in poses)
    measured, error = triangulate_bed_point(pixels, (camera, camera, camera), poses)
    assert measured == pytest.approx(expected, abs=1e-6)
    assert error < 1e-6


def test_generated_targets_have_metric_size_and_detectable_marker(tmp_path):
    pytest.importorskip("numpy")
    cv2 = pytest.importorskip("cv2")
    from forge_calibration.geometry import Checkerboard, detect_marker_center
    from forge_calibration.targets import checkerboard_svg, write_aruco_marker

    board = checkerboard_svg(Checkerboard())
    assert 'width="198.0mm"' in board
    assert 'height="132.0mm"' in board

    marker = tmp_path / "marker.png"
    write_aruco_marker(marker)
    center = detect_marker_center(cv2.imread(str(marker)))
    assert center == pytest.approx((499.5, 499.5), abs=1.0)
