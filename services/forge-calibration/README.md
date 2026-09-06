# Fortress Forge precision calibration

This service measures the toolhead in the printer's bed coordinate system. It
does not infer millimeters from raw pixels and does not move the printer.

## Precision chain

1. Capture every camera at its native 1920x1080 MJPEG resolution.
2. Calibrate each lens from at least 10 distinct views of the supplied metric
   checkerboard.
3. Place the checkerboard flat on the bed and solve each fixed camera's pose in
   bed coordinates.
4. Print the SVG marker at 100% scale (30 mm black marker inside a 40 mm
   white quiet-zone square) and attach it rigidly to the non-moving face of the
   toolhead where at least two cameras can see it.
5. Perform one probe-assisted nozzle touch-off with a measured feeler gauge.
   This registers the fixed marker-to-nozzle transform.
6. Triangulate the marker from every camera that sees it, transform it to the
   nozzle position, and reject the measurement if image quality, visibility,
   calibration RMS, or reprojection error exceeds the configured limit.

A third low side camera is recommended with the present camera placement
because the right/overhead view cannot see the nozzle region. Three cameras do
not replace calibration; they add redundancy and make occlusion detectable.

## Non-negotiable gates

- At least two calibrated cameras must see marker ID 23.
- Captures below 1280x720 are rejected.
- Underexposed, overexposed, or soft views are rejected.
- Intrinsic calibration RMS defaults to <= 0.45 pixels.
- Per-measurement reprojection error defaults to <= 0.75 pixels.
- The generated checkerboard must be printed at 100% / actual size and a square
  must be physically verified as exactly 22.00 mm before use. The default
  198x132 mm board fits US Letter paper without print scaling.
- Camera mounts, focus, zoom, or resolution must not change after calibration.
- The BLTouch remains authoritative for the bed surface. Vision independently
  measures and verifies the registered nozzle position.

## Commands

```bash
python3 -m venv venv
venv/bin/pip install .
forge-calibration generate-targets --output ./targets
forge-calibration capture
forge-calibration inspect-board --images ./current
forge-calibration collect-projective-observations --output ./grid.json --execute-motion
forge-calibration calibrate-projective --observations ./grid.json
forge-calibration calibrate-intrinsics --camera left --images ./left-views
forge-calibration calibrate-intrinsics --camera right --images ./right-views
forge-calibration calibrate-bed-pose --images ./bed-pose
forge-calibration register-touch-off --images ./touch-off --nozzle-x 150 --nozzle-y 150 --gauge-mm 0.10
forge-calibration measure --images ./current
forge-calibration monitor-reference
forge-calibration watch --once
forge-calibration watch
```

`inspect-board` reports the largest visible checkerboard rectangle in each
camera. It never assigns an absolute board origin to a partial, repeating
pattern; uniquely coded toolhead observations at known printer positions are
required to resolve that ambiguity.

The projective workflow uses cold, homed XYZ motion as its metric reference. It
is valid only when all three requested axes physically move the marker. On a
bed-slinger such as the CR-10S Pro V2, Y moves the bed rather than the toolhead,
so a marker-only XYZ fit must fail its pixel and held-out millimeter gates. A
bed-fixed target observation must supply Y. Motion collection is opt-in and
refuses a printing, heated, or non-operational printer. Models are written only
after fit error is at most 0.75 px, held-out RMS is at most 0.25 mm, and the
maximum held-out error is at most 0.50 mm.

`watch` is a local, multi-camera print supervisor. It checks capture quality and
fixed-camera drift on every cycle, runs the configured ONNX print-failure model,
and stores the complete decision record in `monitor/events.jsonl`. An automatic
pause requires the configured confidence from at least two stable cameras for
three consecutive observations, plus a fresh OctoPrint confirmation that the
printer is still printing. It never cancels or resumes a job. Record a new
reference only after the mounts are fixed and before printing.

For the user-local installation on Fortress Forge, install
`forge-calibration-monitor.user.service` as
`~/.config/systemd/user/forge-calibration-monitor.service`, enable it with
`systemctl --user enable --now forge-calibration-monitor.service`, and enable
user lingering so supervision starts at boot without an interactive login.

The service binds to `127.0.0.1:5051` by default. `POST /api/v1/capture`
returns image-quality evidence. `POST /api/v1/measure` returns a metric nozzle
position only after all precision gates pass. It intentionally exposes no motor
or heater controls; guarded motion remains with OctoPrint and printer firmware.
