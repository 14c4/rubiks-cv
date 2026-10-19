"""Write a synthetic dataset: images plus one JSON label file per image (roadmap 2.1).

    python -m cubetrack.synth.generate --out data/synth/v1 --count 2000 [--seed 1] [--workers 8]
                                      [--backgrounds DIR_OR_VIDEO ...] [--hands data/hands]

Cube states are random legal states from the engine (mostly 25-move scrambles, some solved or nearly
solved). Frame i is drawn from a random generator seeded with (seed, i), so it is the same whatever
the number of workers, and `sheet --seed S` shows frames 0, 1, 2... of the dataset with seed S.
Output: <out>/images/000000.jpg, <out>/labels/000000.json (see render.frame_labels), <out>/meta.json.
data/ is git-ignored.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

from cubetrack.cube import SOLVED, apply_moves, state_to_facelets
from cubetrack.cube.facelets import FACES
from cubetrack.synth.hands import HandLibrary
from cubetrack.synth.render import Camera
from cubetrack.synth.scene import Backgrounds, sample_frame

VERSION = 1
MOVES = [f + s for f in FACES for s in ("", "'", "2")]


def random_facelets(rng: np.random.Generator) -> str:
    r = rng.random()
    length = 0 if r < 0.05 else int(rng.integers(1, 4)) if r < 0.15 else 25
    return state_to_facelets(apply_moves(SOLVED, [MOVES[i] for i in rng.integers(len(MOVES), size=length)]))


def make_frame(seed: int, i: int, backgrounds: Backgrounds | None = None, effects: bool = True,
               hands: HandLibrary | None = None):
    """Frame i of the dataset with this seed: (image, labels)."""
    rng = np.random.default_rng([seed, i])
    return sample_frame(rng, random_facelets(rng), backgrounds=backgrounds, effects=effects, hand_library=hands)


_backgrounds = _hands = None  # per worker process


def _start_worker(paths, hands_dir):
    global _backgrounds, _hands
    _backgrounds = Backgrounds(paths, (Camera().width, Camera().height)) if paths else None
    _hands = HandLibrary(hands_dir) if hands_dir else None


def _write_frame(job) -> int:
    seed, i, out = job
    img, labels = make_frame(seed, i, _backgrounds, hands=_hands)
    name = f"{i:06d}"
    cv2.imwrite(str(out / "images" / f"{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    labels["image"] = f"images/{name}.jpg"
    (out / "labels" / f"{name}.json").write_text(json.dumps(labels))
    return i


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--backgrounds", nargs="*", default=[], help="real background images / videos / folders")
    parser.add_argument("--hands", type=Path, help="hand library from cubetrack.synth.hands (else drawn hands)")
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    args = parser.parse_args(argv)

    (args.out / "images").mkdir(parents=True, exist_ok=True)
    (args.out / "labels").mkdir(parents=True, exist_ok=True)
    jobs = [(args.seed, i, args.out) for i in range(args.count)]
    start = time.perf_counter()
    with Pool(args.workers, initializer=_start_worker, initargs=(args.backgrounds, args.hands)) as pool:
        for done, _ in enumerate(pool.imap_unordered(_write_frame, jobs, chunksize=4), 1):
            if done % 100 == 0 or done == args.count:
                print(f"{done}/{args.count} frames, {done / (time.perf_counter() - start):.1f}/s", flush=True)
    meta = {"version": VERSION, "seed": args.seed, "count": args.count, "backgrounds": args.backgrounds,
            "hands": str(args.hands) if args.hands else None,
            "note": "synthetic (cubetrack.synth); a development aid, not evidence of real accuracy"}
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {args.count} frames to {args.out}")


if __name__ == "__main__":
    main()
