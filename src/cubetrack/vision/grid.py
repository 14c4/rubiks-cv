"""Fixed 3x3 guide grid: where to sample the nine stickers of a face held in front of the camera.

This is the "guided region of interest" stand-in for real face detection (roadmap 5.1): the user
lines the cube up with the drawn grid; nothing here finds the cube by itself.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class GuideGrid:
    x: int  # top-left corner of the whole grid, pixels
    y: int
    cell: int  # side of one cell, pixels
    margin: int  # pixels skipped on each side of a cell (sticker edges, gaps, drawn lines)

    @classmethod
    def centered(cls, width: int, height: int, fraction: float = 0.5) -> GuideGrid:
        """A grid in the middle of the frame whose side is `fraction` of the shorter frame side."""
        cell = int(min(width, height) * fraction) // 3
        return cls((width - 3 * cell) // 2, (height - 3 * cell) // 2, cell, cell // 4)

    def boxes(self):
        """Yield (row, col, x1, y1, x2, y2) of each cell's sampling area, row-major."""
        for row in range(3):
            for col in range(3):
                x1 = self.x + col * self.cell + self.margin
                y1 = self.y + row * self.cell + self.margin
                yield row, col, x1, y1, x1 + self.cell - 2 * self.margin, y1 + self.cell - 2 * self.margin

    def sample_bgr(self, frame: np.ndarray) -> np.ndarray:
        """(3, 3, 3) float: mean B, G, R of each cell's sampling area."""
        return self.sample(frame)[0]

    def sample(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Mean B, G, R per cell (3, 3, 3) and lightness spread per cell (3, 3).

        The spread is the standard deviation of 8-bit L inside the box. A box fully on one sticker
        has a small spread (at most about 2.4 in the 2026-10-18b frames); a box straddling a sticker
        edge, the dark gap or the background has a large one (about 40).
        """
        means, spread = np.zeros((3, 3, 3)), np.zeros((3, 3))
        for row, col, x1, y1, x2, y2 in self.boxes():
            patch = frame[y1:y2, x1:x2]
            if patch.size == 0 or x1 < 0 or y1 < 0:
                raise ValueError("guide grid lies outside the frame")
            means[row, col] = patch.mean(axis=(0, 1))
            spread[row, col] = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB)[..., 0].std()
        return means, spread

    def moved(self, dx: int = 0, dy: int = 0, dcell: int = 0) -> GuideGrid:
        """A copy shifted by (dx, dy) pixels and/or with cells dcell pixels larger (margin follows)."""
        cell = max(12, self.cell + dcell)
        return GuideGrid(self.x + dx - 3 * (cell - self.cell) // 2, self.y + dy - 3 * (cell - self.cell) // 2,
                         cell, cell // 4)

    def fits(self, width: int, height: int) -> bool:
        return self.x >= 0 and self.y >= 0 and self.x + 3 * self.cell <= width and self.y + 3 * self.cell <= height


UNEVEN_SPREAD = 8.0  # lightness std above this means the box is not on a single uniform sticker


def uneven_cells(spread: np.ndarray, skip_center: bool = True) -> np.ndarray:
    """(9,) bool, row-major: True where a cell's spread says the box is not on one sticker.

    The center is skipped by default: logos make it textured on purpose.
    """
    flags = np.asarray(spread).reshape(-1) > UNEVEN_SPREAD
    if skip_center:
        flags[4] = False
    return flags


def bgr_means_to_lab8(bgr_means: np.ndarray) -> np.ndarray:
    """Convert mean BGR values (any shape ending in 3) to OpenCV 8-bit Lab of the same shape.

    Average in BGR first, then convert: the classifier was calibrated on values made this way.
    """
    bgr8 = np.round(np.asarray(bgr_means)).clip(0, 255).astype(np.uint8)
    shape = bgr8.shape
    return cv2.cvtColor(bgr8.reshape(1, -1, 3), cv2.COLOR_BGR2LAB).reshape(shape)
