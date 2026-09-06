from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify

from .capture import capture_set, capture_skew_ms
from .config import load_config
from .measurement import measure_marker, measure_projective_nozzle
from .quality import assess_image
from .state import load_touch_off


def create_app(config_path: str | Path) -> Flask:
    config = load_config(config_path)
    app = Flask(__name__)

    @app.errorhandler(ValueError)
    def invalid_measurement(error):
        return jsonify({"precision_ready": False, "error": str(error)}), 422

    @app.get("/healthz")
    def health():
        models = config.state_dir / "models"
        return jsonify(
            {
                "status": "ok",
                "camera_count": len(config.cameras),
                "camera_names": [camera.name for camera in config.cameras],
                "touch_off_registered": (models / "touch-off.json").exists(),
                "mode": "measurement-only",
            }
        )

    @app.post("/api/v1/capture")
    def capture():
        frames = capture_set(config.cameras, config.state_dir / "captures")
        results = []
        for frame in frames:
            results.append(
                {
                    "camera": frame.camera,
                    "path": str(frame.path),
                    "quality": assess_image(frame.path, config.quality).as_dict(),
                }
            )
        return jsonify(
            {
                "capture_skew_ms": capture_skew_ms(frames),
                "frames": results,
                "image_quality_ready": all(item["quality"]["passed"] for item in results),
                "precision_ready": False,
                "next_gate": "metric camera models, bed poses, and nozzle touch-off",
            }
        )

    @app.post("/api/v1/measure")
    def measure():
        frames = capture_set(config.cameras, config.state_dir / "captures")
        images = {frame.camera: frame.path for frame in frames}
        projective_models = [
            config.state_dir / "models" / f"{camera.name}-projective.npz"
            for camera in config.cameras
        ]
        if sum(path.exists() for path in projective_models) >= 2:
            nozzle, error, visible = measure_projective_nozzle(config, images)
            return jsonify(
                {
                    "precision_ready": True,
                    "method": "known-XYZ projective calibration",
                    "nozzle_xyz_mm": nozzle,
                    "nozzle_gap_mm": nozzle[2],
                    "visible_cameras": visible,
                    "reprojection_error_px": error,
                    "capture_skew_ms": capture_skew_ms(frames),
                }
            )
        marker, error, visible = measure_marker(config, images)
        touch = load_touch_off(config.state_dir / "models" / "touch-off.json")
        nozzle = touch.nozzle_xyz(marker)
        return jsonify(
            {
                "precision_ready": True,
                "marker_xyz_mm": marker,
                "nozzle_xyz_mm": nozzle,
                "nozzle_gap_mm": nozzle[2],
                "visible_cameras": visible,
                "reprojection_error_px": error,
                "capture_skew_ms": capture_skew_ms(frames),
            }
        )

    return app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/forge-calibration/config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5051)
    args = parser.parse_args()
    create_app(args.config).run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
