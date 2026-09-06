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
from forge_calibration.monitor import CameraObservation, Consensus
from forge_calibration.config import MonitorConfig


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


def test_projective_calibration_recovers_metric_3d_points():
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from forge_calibration.geometry import (
        calibrate_projective_camera,
        triangulate_projective_point,
    )

    grid = np.asarray(
        [(x, y, z) for z in (60.0, 120.0, 180.0) for y in (80.0, 150.0, 220.0) for x in (80.0, 150.0, 220.0)]
    )
    projections = (
        np.array([[900.0, 10.0, 400.0, 100000.0], [5.0, 920.0, 300.0, 50000.0], [0.01, 0.02, 1.0, 800.0]]),
        np.array([[850.0, -20.0, 500.0, 80000.0], [15.0, 900.0, 350.0, 60000.0], [-0.03, 0.01, 1.0, 900.0]]),
    )

    def project(matrix, point):
        pixel = matrix @ np.append(point, 1.0)
        return pixel[:2] / pixel[2]

    pixel_sets = [np.asarray([project(matrix, point) for point in grid]) for matrix in projections]
    models = tuple(calibrate_projective_camera(grid, pixels) for pixels in pixel_sets)
    expected = np.array([123.0, 177.0, 93.0])
    pixels = tuple(tuple(project(matrix, expected)) for matrix in projections)
    measured, error = triangulate_projective_point(pixels, models)
    assert measured == pytest.approx(expected, abs=1e-6)
    assert error < 1e-6


def test_bed_slinger_model_uses_both_marker_tracks():
    np = pytest.importorskip("numpy")
    from forge_calibration.bed_slinger import calibrate_bed_slinger_camera

    points = np.asarray(
        [(x, y, z) for z in (5.0, 15.0, 30.0) for y in (100.0, 150.0, 200.0) for x in (100.0, 150.0, 200.0)]
    )
    features = []
    for x, y, z in points:
        toolhead = (2.0 * x + 0.3 * z, -0.2 * x + 3.0 * z)
        bed = (500.0 + 0.5 * y + 0.001 * y**2, 800.0 - 1.2 * y)
        features.append((*toolhead, *bed))
    model = calibrate_bed_slinger_camera(np.asarray(features), points)
    test = np.asarray((135.0, 175.0, 12.0))
    x, y, z = test
    predicted = model.predict(
        (2.0 * x + 0.3 * z, -0.2 * x + 3.0 * z),
        (500.0 + 0.5 * y + 0.001 * y**2, 800.0 - 1.2 * y),
    )
    assert predicted == pytest.approx(test, abs=0.05)


def test_toolhead_plane_model_recovers_xz():
    np = pytest.importorskip("numpy")
    from forge_calibration.bed_slinger import calibrate_toolhead_plane_camera

    points = np.asarray(
        [(x, z) for z in (5.0, 15.0, 30.0) for x in (110.0, 140.0, 170.0, 200.0)]
    )
    pixels = np.asarray(
        [(2.0 * x + 0.3 * z + 0.0005 * x**2, -0.2 * x + 3.0 * z) for x, z in points]
    )
    model = calibrate_toolhead_plane_camera(pixels, points)
    expected = np.asarray((155.0, 12.0))
    x, z = expected
    predicted = model.predict_xz(
        (2.0 * x + 0.3 * z + 0.0005 * x**2, -0.2 * x + 3.0 * z)
    )
    assert predicted == pytest.approx(expected, abs=0.05)


def test_generated_targets_have_metric_size_and_detectable_marker(tmp_path):
    pytest.importorskip("numpy")
    cv2 = pytest.importorskip("cv2")
    from forge_calibration.geometry import Checkerboard, detect_marker_center
    from forge_calibration.targets import checkerboard_svg, letter_aruco_svg, write_aruco_marker

    board = checkerboard_svg(Checkerboard())
    assert 'width="198.0mm"' in board
    assert 'height="132.0mm"' in board

    marker_page = letter_aruco_svg()
    assert 'width="215.9mm"' in marker_page
    assert 'height="279.4mm"' in marker_page
    assert 'black square 30.0 mm' in marker_page
    assert 'ArUco 4x4 ID 24' in letter_aruco_svg(marker_id=24)

    marker = tmp_path / "marker.png"
    write_aruco_marker(marker)
    center = detect_marker_center(cv2.imread(str(marker)))
    assert center == pytest.approx((499.5, 499.5), abs=1.0)


def test_partial_checkerboard_reports_visible_grid_without_assigning_origin():
    np = pytest.importorskip("numpy")
    cv2 = pytest.importorskip("cv2")
    from forge_calibration.geometry import Checkerboard, find_partial_checkerboard

    square = 80
    image = np.full((8 * square, 11 * square, 3), 255, dtype=np.uint8)
    for row in range(6):
        for column in range(9):
            if (row + column) % 2 == 0:
                cv2.rectangle(
                    image,
                    ((column + 1) * square, (row + 1) * square),
                    ((column + 2) * square, (row + 2) * square),
                    (0, 0, 0),
                    thickness=-1,
                )
    image = image[:, 2 * square :]
    detected = find_partial_checkerboard(image, Checkerboard())
    assert detected.columns == 7
    assert detected.rows == 5
    assert len(detected.corners) == detected.columns * detected.rows


def observation(camera, score, stable=True, quality=True):
    return CameraObservation(camera, f"/{camera}.jpg", quality, score, 0.0, 0.0, stable)


def test_monitor_requires_repeated_multi_camera_agreement_before_pause():
    consensus = Consensus(MonitorConfig(confirmations_required=3, cameras_required=2))
    frames = (observation("left", 0.9), observation("right", 0.8), observation("side", 0.1))
    assert not consensus.decide(True, frames).pause_requested
    assert not consensus.decide(True, frames).pause_requested
    decision = consensus.decide(True, frames)
    assert decision.pause_requested
    assert decision.agreeing_cameras == ("left", "right")


def test_monitor_never_pauses_idle_printer_or_on_one_camera():
    consensus = Consensus(MonitorConfig(confirmations_required=2, cameras_required=2))
    one_view = (observation("left", 0.9), observation("right", 0.1))
    consensus.decide(True, one_view)
    assert not consensus.decide(True, one_view).pause_requested
    both = (observation("left", 0.9), observation("right", 0.9))
    consensus.decide(False, both)
    assert not consensus.decide(False, both).pause_requested


def test_shifted_camera_is_excluded_from_failure_consensus():
    consensus = Consensus(MonitorConfig(confirmations_required=1, cameras_required=2))
    frames = (observation("left", 0.9, stable=False), observation("right", 0.9))
    decision = consensus.decide(True, frames)
    assert not decision.pause_requested
    assert "camera mount moved: left" in decision.reasons
