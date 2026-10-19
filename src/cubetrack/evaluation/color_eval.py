"""Cross-session check of the color classifier on labelled fixture sessions.

    python -m cubetrack.evaluation.color_eval [--fixtures DIR]

For every session used as calibration, classify every OTHER session (also artificially dimmed, as a
stand-in for shadow) and count: confident and correct / correct but low confidence / unknown / WRONG.
WRONG (a confident-looking different color) is the number that must stay at zero; unknown is honest.
Labels come from the owner (which solved face was shown), never from the classifier.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from cubetrack.vision.color import ColorModel

DEFAULT_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "color"
CENTER = 4  # row-major index of cell (1, 1)
CENTER_MASK = np.arange(9) == CENTER
CONFIDENT = 0.90
DIMMING = (1.0, 0.8, 0.6, 0.5)
# Things that are not stickers, as BGR. Gray is absent on purpose: a white sticker in shadow is gray.
FOREIGN = {"dark table": (30, 30, 35), "light skin": (150, 170, 225), "dark skin": (80, 105, 160)}


@dataclass
class Face:
    label: str  # the color the owner showed
    pose: str  # "flat" or a stress pose such as "tilt_toward"
    bgr: np.ndarray  # (9, 3) float, row-major cells


def bgr_to_lab8(bgr) -> np.ndarray:
    """(N, 3) BGR means -> (N, 3) OpenCV 8-bit Lab."""
    b = np.clip(np.round(np.asarray(bgr, float)), 0, 255).astype(np.uint8).reshape(1, -1, 3)
    return cv2.cvtColor(b, cv2.COLOR_BGR2LAB).reshape(-1, 3)


def load_session(name: str, fixtures: Path = DEFAULT_FIXTURES) -> list[Face]:
    data = json.loads((fixtures / f"session_{name}.json").read_text())
    return [Face(f["label"], f["pose"], np.array(f["bgr"], float).reshape(9, 3)) for f in data["faces"]]


def session_names(fixtures: Path = DEFAULT_FIXTURES) -> list[str]:
    return sorted(p.stem.removeprefix("session_") for p in fixtures.glob("session_*.json"))


def calibrate(faces: list[Face]) -> ColorModel:
    """Fit the way the live app does: flat faces only; centers kept apart (logos)."""
    samples, centers = {}, {}
    for f in faces:
        if f.pose == "flat":
            lab = bgr_to_lab8(f.bgr)
            samples.setdefault(f.label, []).extend(np.delete(lab, CENTER, axis=0))
            centers.setdefault(f.label, []).append(lab[CENTER])
    return ColorModel.fit({c: np.array(v) for c, v in samples.items()},
                          {c: np.array(v) for c, v in centers.items()})


def score(model: ColorModel, faces: list[Face], dim: float = 1.0) -> dict[str, int]:
    counts = {"ok": 0, "low": 0, "unknown": 0, "wrong": 0}
    for f in faces:
        for est in model.classify(bgr_to_lab8(np.clip(f.bgr * dim, 0, 255)), centers=CENTER_MASK):
            if est.label is None:
                counts["unknown"] += 1
            elif est.label != f.label:
                counts["wrong"] += 1
            elif est.confidence >= CONFIDENT:
                counts["ok"] += 1
            else:
                counts["low"] += 1
    return counts


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args(argv)

    names = session_names(args.fixtures)
    sessions = {n: load_session(n, args.fixtures) for n in names}
    print("cells: ok (correct, >= 90%) / low (correct, < 90%) / unknown / WRONG; dimming simulates shadow")
    for src in names:
        model = calibrate(sessions[src])
        for dst in names:
            if dst == src:
                continue
            row = []
            for dim in DIMMING:
                c = score(model, sessions[dst], dim)
                row.append(f"x{dim}: {c['ok']:3d}/{c['low']}/{c['unknown']}/W{c['wrong']}")
            print(f"calibrate {src} -> {dst}  ({sum(9 for _ in sessions[dst])} cells)  " + "   ".join(row))
        foreign = {k: model.classify(bgr_to_lab8([v]))[0] for k, v in FOREIGN.items()}
        accepted = [f"{k} -> {e.label} {e.confidence:.0%}" for k, e in foreign.items() if e.label is not None]
        print(f"  non-sticker samples given a color: {', '.join(accepted) or 'none'} (below 90% shows as uncertain)")


if __name__ == "__main__":
    main()
