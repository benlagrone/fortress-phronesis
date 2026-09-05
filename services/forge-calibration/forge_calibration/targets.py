from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .geometry import Checkerboard


def checkerboard_svg(board: Checkerboard) -> str:
    columns = board.inner_columns + 1
    rows = board.inner_rows + 1
    width = columns * board.square_mm
    height = rows * board.square_mm
    squares = []
    for row in range(rows):
        for column in range(columns):
            if (row + column) % 2 == 0:
                squares.append(
                    f'<rect x="{column * board.square_mm}mm" '
                    f'y="{row * board.square_mm}mm" width="{board.square_mm}mm" '
                    f'height="{board.square_mm}mm" fill="#000"/>'
                )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" '
        f'height="{height}mm" viewBox="0 0 {width} {height}">\n'
        f'<rect width="{width}" height="{height}" fill="#fff"/>\n'
        + "\n".join(squares)
        + "\n</svg>\n"
    )


def write_checkerboard(path: Path, board: Checkerboard) -> None:
    path.write_text(checkerboard_svg(board))


def write_aruco_marker(path: Path, marker_id: int = 23, pixels: int = 1000) -> None:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    quiet_zone = pixels // 10
    marker_pixels = pixels - 2 * quiet_zone
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, marker_pixels, borderBits=1)
    image = np.full((pixels, pixels), 255, dtype=np.uint8)
    image[quiet_zone : quiet_zone + marker_pixels, quiet_zone : quiet_zone + marker_pixels] = marker
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"failed to write {path}")


def aruco_svg(marker_id: int = 23, size_mm: float = 30.0) -> str:
    modules = 6  # 4x4 payload plus a one-module black border.
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    raster = cv2.aruco.generateImageMarker(dictionary, marker_id, modules * 20, borderBits=1)
    cells = cv2.resize(raster, (modules, modules), interpolation=cv2.INTER_AREA)
    quiet_modules = 1
    canvas_modules = modules + 2 * quiet_modules
    canvas_mm = size_mm * canvas_modules / modules
    shifted = []
    for row, column in np.argwhere(cells < 128):
        shifted.append(
            f'<rect x="{column + quiet_modules}" y="{row + quiet_modules}" '
            'width="1" height="1" fill="#000"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_mm}mm" '
        f'height="{canvas_mm}mm" viewBox="0 0 {canvas_modules} {canvas_modules}" shape-rendering="crispEdges">\n'
        f'<rect width="{canvas_modules}" height="{canvas_modules}" fill="#fff"/>\n'
        + "\n".join(shifted)
        + "\n</svg>\n"
    )


def write_aruco_svg(path: Path, marker_id: int = 23, size_mm: float = 30.0) -> None:
    path.write_text(aruco_svg(marker_id, size_mm))
