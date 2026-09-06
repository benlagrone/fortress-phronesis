from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .capture import capture_set, capture_skew_ms
from .bed_slinger_workflow import (
    calibrate_bed_slinger_observations,
    collect_bed_slinger_observations,
)
from .config import load_config
from .geometry import (
    Checkerboard,
    calibrate_intrinsics,
    find_partial_checkerboard,
    load_camera_model,
    save_bed_pose,
    save_camera_model,
    solve_bed_pose,
)
from .quality import assess_image
from .measurement import measure_marker, measure_projective_nozzle
from .monitor import PrintMonitor
from .octoprint import OctoPrintClient
from .projective import calibrate_observations, collect_observations
from .state import TouchOff, load_touch_off, save_touch_off
from .targets import write_aruco_marker, write_aruco_svg, write_checkerboard, write_letter_aruco_svg


def _image(path: Path):
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"unable to decode {path}")
    return image


def _json(value) -> None:
    print(json.dumps(value, indent=2))


def command_targets(args) -> None:
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=True)
    board = Checkerboard(args.columns, args.rows, args.square_mm)
    write_checkerboard(destination / "bed-checkerboard.svg", board)
    write_aruco_marker(destination / "toolhead-marker-23.png", marker_id=23)
    write_aruco_svg(destination / "toolhead-marker-23.svg", marker_id=23, size_mm=30.0)
    write_letter_aruco_svg(
        destination / "toolhead-marker-23-letter.svg", marker_id=23, size_mm=30.0
    )
    write_aruco_svg(destination / "bed-marker-24.svg", marker_id=24, size_mm=30.0)
    write_letter_aruco_svg(
        destination / "bed-marker-24-letter.svg", marker_id=24, size_mm=30.0
    )
    _json(
        {
            "checkerboard": str(destination / "bed-checkerboard.svg"),
            "marker": str(destination / "toolhead-marker-23.png"),
            "metric_marker": str(destination / "toolhead-marker-23.svg"),
            "printable_metric_marker": str(destination / "toolhead-marker-23-letter.svg"),
            "bed_marker": str(destination / "bed-marker-24.svg"),
            "printable_bed_marker": str(destination / "bed-marker-24-letter.svg"),
            "print_scale": "100% / actual size; disable fit-to-page",
            "verification": f"one checkerboard square must measure {args.square_mm:.3f} mm",
        }
    )


def command_inspect_board(args) -> None:
    board = Checkerboard(args.columns, args.rows, args.square_mm)
    results = []
    for image_path in sorted(Path(args.images).glob("*.jpg")):
        try:
            detection = find_partial_checkerboard(_image(image_path), board)
            results.append(
                {
                    "camera": image_path.stem,
                    "detected": True,
                    "columns": detection.columns,
                    "rows": detection.rows,
                    "corners": len(detection.corners),
                    "absolute_origin_resolved": detection.corners.shape[0]
                    == board.inner_columns * board.inner_rows,
                }
            )
        except ValueError as error:
            results.append(
                {"camera": image_path.stem, "detected": False, "error": str(error)}
            )
    _json(
        {
            "views": results,
            "origin_gate": "partial views require uniquely coded toolhead observations",
        }
    )


def command_capture(args) -> None:
    config = load_config(args.config)
    frames = capture_set(config.cameras, config.state_dir / "captures")
    quality = [assess_image(frame.path, config.quality).as_dict() for frame in frames]
    _json(
        {
            "capture_skew_ms": capture_skew_ms(frames),
            "frames": [
                {"camera": frame.camera, "path": str(frame.path), "quality": result}
                for frame, result in zip(frames, quality)
            ],
            "image_quality_ready": all(item["passed"] for item in quality),
            "precision_ready": False,
            "next_gate": "metric camera models, bed poses, and nozzle touch-off",
        }
    )


def command_intrinsics(args) -> None:
    config = load_config(args.config)
    board = Checkerboard(args.columns, args.rows, args.square_mm)
    camera = next(camera for camera in config.cameras if camera.name == args.camera)
    paths = sorted(Path(args.images).glob("*.jpg"))
    model = calibrate_intrinsics((_image(path) for path in paths), board)
    if model.rms_px > config.quality.maximum_intrinsic_rms_px:
        raise ValueError(
            f"intrinsic RMS {model.rms_px:.3f}px exceeds precision gate "
            f"{config.quality.maximum_intrinsic_rms_px:.3f}px"
        )
    destination = config.state_dir / "models" / f"{camera.name}-intrinsics.npz"
    save_camera_model(destination, model)
    _json({"camera": camera.name, "rms_px": model.rms_px, "path": str(destination)})


def command_bed_pose(args) -> None:
    config = load_config(args.config)
    board = Checkerboard(args.columns, args.rows, args.square_mm)
    results = []
    for camera in config.cameras:
        model = load_camera_model(config.state_dir / "models" / f"{camera.name}-intrinsics.npz")
        image_path = Path(args.images) / f"{camera.name}.jpg"
        pose = solve_bed_pose(_image(image_path), board, model)
        if pose.reprojection_rms_px > config.quality.maximum_reprojection_error_px:
            raise ValueError(
                f"{camera.name} bed-pose error {pose.reprojection_rms_px:.3f}px exceeds gate"
            )
        destination = config.state_dir / "models" / f"{camera.name}-bed-pose.npz"
        save_bed_pose(destination, pose)
        results.append(
            {"camera": camera.name, "rms_px": pose.reprojection_rms_px, "path": str(destination)}
        )
    _json({"poses": results})


def _images(config, image_dir: Path):
    return {
        camera.name: image_dir / f"{camera.name}.jpg"
        for camera in config.cameras
        if (image_dir / f"{camera.name}.jpg").exists()
    }


def _measure(config, image_dir: Path):
    return measure_marker(config, _images(config, image_dir))


def command_touch_off(args) -> None:
    config = load_config(args.config)
    marker, error, visible = _measure(config, Path(args.images))
    nozzle = (args.nozzle_x, args.nozzle_y, args.gauge_mm)
    touch = TouchOff.create(marker, nozzle, args.gauge_mm)
    destination = config.state_dir / "models" / "touch-off.json"
    save_touch_off(destination, touch)
    _json(
        {
            "marker_xyz_mm": marker,
            "nozzle_xyz_mm": nozzle,
            "visible_cameras": visible,
            "reprojection_error_px": error,
            "path": str(destination),
        }
    )


def command_measure(args) -> None:
    config = load_config(args.config)
    projective_models = [
        config.state_dir / "models" / f"{camera.name}-projective.npz"
        for camera in config.cameras
    ]
    if sum(path.exists() for path in projective_models) >= 2:
        nozzle, error, visible = measure_projective_nozzle(
            config, _images(config, Path(args.images))
        )
        _json(
            {
                "precision_ready": True,
                "method": "known-XYZ projective calibration",
                "nozzle_xyz_mm": nozzle,
                "nozzle_gap_mm": nozzle[2],
                "visible_cameras": visible,
                "reprojection_error_px": error,
            }
        )
        return
    marker, error, visible = _measure(config, Path(args.images))
    touch = load_touch_off(config.state_dir / "models" / "touch-off.json")
    nozzle = touch.nozzle_xyz(marker)
    _json(
        {
            "precision_ready": True,
            "marker_xyz_mm": marker,
            "nozzle_xyz_mm": nozzle,
            "nozzle_gap_mm": nozzle[2],
            "visible_cameras": visible,
            "reprojection_error_px": error,
        }
    )


def _float_values(raw: str) -> tuple[float, ...]:
    return tuple(float(value) for value in raw.split(","))


def command_collect_projective(args) -> None:
    if not args.execute_motion:
        raise ValueError("motion collection requires --execute-motion")
    config = load_config(args.config)
    payload = collect_observations(
        config,
        Path(args.output),
        _float_values(args.x),
        _float_values(args.y),
        _float_values(args.z),
        args.settle_seconds,
    )
    _json({"output": args.output, "positions": len(payload["observations"])})


def command_calibrate_projective(args) -> None:
    config = load_config(args.config)
    _json(calibrate_observations(config, Path(args.observations)))


def command_collect_bed_slinger(args) -> None:
    if not args.execute_motion:
        raise ValueError("motion collection requires --execute-motion")
    config = load_config(args.config)
    payload = collect_bed_slinger_observations(
        config,
        Path(args.output),
        _float_values(args.x),
        _float_values(args.y),
        _float_values(args.z),
        args.settle_seconds,
    )
    _json({"output": args.output, "positions": len(payload["observations"])})


def command_calibrate_bed_slinger(args) -> None:
    config = load_config(args.config)
    _json(calibrate_bed_slinger_observations(config, Path(args.observations)))


def _monitor(config):
    client = OctoPrintClient.from_config_file(
        config.octoprint_url, config.octoprint_api_key_file
    )
    return PrintMonitor(config, client)


def command_monitor_reference(args) -> None:
    config = load_config(args.config)
    _json({"references": _monitor(config).record_reference()})


def command_watch(args) -> None:
    config = load_config(args.config)
    monitor = _monitor(config)
    if args.once:
        _json(monitor.observe_once())
    else:
        monitor.watch()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="forge-calibration")
    root.add_argument("--config", default="/etc/forge-calibration/config.yaml")
    commands = root.add_subparsers(dest="command", required=True)

    targets = commands.add_parser("generate-targets")
    targets.add_argument("--output", required=True)
    targets.add_argument("--columns", type=int, default=8)
    targets.add_argument("--rows", type=int, default=5)
    targets.add_argument("--square-mm", type=float, default=22.0)
    targets.set_defaults(handler=command_targets)

    capture = commands.add_parser("capture")
    capture.set_defaults(handler=command_capture)

    intrinsics = commands.add_parser("calibrate-intrinsics")
    intrinsics.add_argument("--camera", required=True)
    intrinsics.add_argument("--images", required=True)
    intrinsics.add_argument("--columns", type=int, default=8)
    intrinsics.add_argument("--rows", type=int, default=5)
    intrinsics.add_argument("--square-mm", type=float, default=22.0)
    intrinsics.set_defaults(handler=command_intrinsics)

    bed = commands.add_parser("calibrate-bed-pose")
    bed.add_argument("--images", required=True)
    bed.add_argument("--columns", type=int, default=8)
    bed.add_argument("--rows", type=int, default=5)
    bed.add_argument("--square-mm", type=float, default=22.0)
    bed.set_defaults(handler=command_bed_pose)

    inspect = commands.add_parser("inspect-board")
    inspect.add_argument("--images", required=True)
    inspect.add_argument("--columns", type=int, default=8)
    inspect.add_argument("--rows", type=int, default=5)
    inspect.add_argument("--square-mm", type=float, default=22.0)
    inspect.set_defaults(handler=command_inspect_board)

    touch = commands.add_parser("register-touch-off")
    touch.add_argument("--images", required=True)
    touch.add_argument("--nozzle-x", type=float, required=True)
    touch.add_argument("--nozzle-y", type=float, required=True)
    touch.add_argument("--gauge-mm", type=float, required=True)
    touch.set_defaults(handler=command_touch_off)

    measure = commands.add_parser("measure")
    measure.add_argument("--images", required=True)
    measure.set_defaults(handler=command_measure)

    collect = commands.add_parser("collect-projective-observations")
    collect.add_argument("--output", required=True)
    collect.add_argument("--x", default="80,150,220")
    collect.add_argument("--y", default="80,150,220")
    collect.add_argument("--z", default="60,120,180")
    collect.add_argument("--settle-seconds", type=float, default=5.0)
    collect.add_argument("--execute-motion", action="store_true")
    collect.set_defaults(handler=command_collect_projective)

    projective = commands.add_parser("calibrate-projective")
    projective.add_argument("--observations", required=True)
    projective.set_defaults(handler=command_calibrate_projective)

    slinger_collect = commands.add_parser("collect-bed-slinger-observations")
    slinger_collect.add_argument("--output", required=True)
    slinger_collect.add_argument("--x", default="100,150,200")
    slinger_collect.add_argument("--y", default="100,150,200")
    slinger_collect.add_argument("--z", default="5,15,30")
    slinger_collect.add_argument("--settle-seconds", type=float, default=5.0)
    slinger_collect.add_argument("--execute-motion", action="store_true")
    slinger_collect.set_defaults(handler=command_collect_bed_slinger)

    slinger = commands.add_parser("calibrate-bed-slinger")
    slinger.add_argument("--observations", required=True)
    slinger.set_defaults(handler=command_calibrate_bed_slinger)

    reference = commands.add_parser("monitor-reference")
    reference.set_defaults(handler=command_monitor_reference)

    watch = commands.add_parser("watch")
    watch.add_argument("--once", action="store_true")
    watch.set_defaults(handler=command_watch)
    return root


def main() -> None:
    args = parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
