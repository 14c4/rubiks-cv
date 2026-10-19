"""Contact sheets: look at synthetic frames, their labels, and real frames side by side (roadmap 2.1).

    python -m cubetrack.synth.sheet --out sheet.png [--count 12] [--seed 1] [--labels]
    python -m cubetrack.synth.sheet --out compare.png --real recordings/clips/inspection.mp4 [--backgrounds ...]

--labels draws what the model will learn: face outlines (first corner marked: the face's top-left
in the standard view), tile centers (filled = visible, hollow = mostly covered), cube corners.
--real puts real frames (images, folders or videos) in the left column and renders in the right,
for the owner's judgement of how close the renders look.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from cubetrack.synth.generate import make_frame
from cubetrack.synth.hands import HandLibrary
from cubetrack.synth.render import Camera, REAL_BGR
from cubetrack.synth.scene import Backgrounds

CELL = (320, 240)


def draw_labels(img: np.ndarray, labels: dict) -> np.ndarray:
    out = img.copy()
    for face in labels["faces"]:
        color = tuple(int(c) for c in np.clip(np.array(REAL_BGR[face["color"]]) * 0.6 + 100, 0, 255))
        outline = np.array(face["outline"])
        cv2.polylines(out, [np.round(outline * 4).astype(np.int32)], True, (255, 0, 255), 1, cv2.LINE_AA, shift=2)
        cv2.circle(out, tuple(np.round(outline[0]).astype(int)), 4, (255, 0, 255), -1)
        for tile in face["tiles"]:
            c = tuple(np.round(tile["center"]).astype(int))
            cv2.circle(out, c, 3, color, -1 if tile["visible"] > 0.5 else 1, cv2.LINE_AA)
    for corner in labels["corners"]:
        if corner["visible"] and corner["in_frame"]:
            xy = tuple(np.round(corner["xy"]).astype(int))
            cv2.drawMarker(out, xy, (0, 0, 255) if corner["occluded"] else (0, 255, 255),
                           cv2.MARKER_TILTED_CROSS if corner["occluded"] else cv2.MARKER_CROSS, 8, 1)
    return out


def real_frames(paths, count: int, rng: np.random.Generator) -> list[np.ndarray]:
    frames = Backgrounds(paths, (Camera().width, Camera().height), frames_per_video=200).frames
    if not frames:
        raise SystemExit(f"no images or videos found in {paths}")
    picks = rng.choice(len(frames), size=min(count, len(frames)), replace=False)
    return [frames[i] for i in sorted(picks)]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--labels", action="store_true", help="draw the labels on the synthetic frames")
    parser.add_argument("--real", nargs="*", default=[], help="real frames for a side-by-side comparison")
    parser.add_argument("--backgrounds", nargs="*", default=[], help="real background images / videos / folders")
    parser.add_argument("--hands", type=Path, help="hand library from cubetrack.synth.hands (else drawn hands)")
    parser.add_argument("--no-effects", action="store_true", help="skip camera effects (cleaner, for checking)")
    args = parser.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    backgrounds = Backgrounds(args.backgrounds, (Camera().width, Camera().height)) if args.backgrounds else None
    hands = HandLibrary(args.hands) if args.hands else None
    synth = []
    for i in range(args.count):  # frames 0.. of the dataset with this seed
        img, labels = make_frame(args.seed, i, backgrounds, effects=not args.no_effects, hands=hands)
        synth.append(draw_labels(img, labels) if args.labels else img)
    if args.real:
        real = real_frames(args.real, args.count, rng)
        rows = [np.hstack([cv2.resize(r, CELL), cv2.resize(s, CELL)]) for r, s in zip(real, synth)]
    else:
        cells = [cv2.resize(s, CELL) for s in synth]
        cells += [np.zeros_like(cells[0])] * (-len(cells) % 4)
        rows = [np.hstack(cells[i:i + 4]) for i in range(0, len(cells), 4)]
    sheet = np.vstack(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.out), sheet)
    print(f"wrote {args.out} ({sheet.shape[1]}x{sheet.shape[0]})")


if __name__ == "__main__":
    main()
