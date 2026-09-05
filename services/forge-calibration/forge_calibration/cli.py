from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .capture import capture_set, capture_skew_ms
from .config import load_config
from .geometry import (
    Checkerboard,
    calibrate_intrinsics,
    load_camera_model,
    save_bed_pose,
    save_camera_model,
    solve_bed_pose,
)
from .quality import assess_image
from .measurement import measure_marker
from .monitor import PrintMonitor
from .octoprint import OctoPrintClient
from .state import TouchOff, load_touch_off, save_touch_off
from .targets import write_aruco_marker, write_aruco_svg, write_checkerboard


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
    _json(
        {
            "checkerboard": str(destination / "bed-checkerboard.svg"),
            "marker": str(destination / "toolhead-marker-23.png"),
            "metric_marker": str(destination / "toolhead-marker-23.svg"),
            "print_scale": "100% / actual size; disable fit-to-page",
            "verification": f"one checkerboard square must measure {args.square_mm:.3f} mm",
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


def _measure(config, image_dir: Path):
    images = {
        camera.name: image_dir / f"{camera.name}.jpg"
        for camera in config.cameras
        if (image_dir / f"{camera.name}.jpg").exists()
    }
    return measure_marker(config, images)


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

    touch = commands.add_parser("register-touch-off")
    touch.add_argument("--images", required=True)
    touch.add_argument("--nozzle-x", type=float, required=True)
    touch.add_argument("--nozzle-y", type=float, required=True)
    touch.add_argument("--gauge-mm", type=float, required=True)
    touch.set_defaults(handler=command_touch_off)

    measure = commands.add_parser("measure")
    measure.add_argument("--images", required=True)
    measure.set_defaults(handler=command_measure)

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
