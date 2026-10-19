"""Assembly (2.5) under simulated inspection readings: how often is the cube read exactly, and is it ever wrong?

    python -m cubetrack.evaluation.assembly_eval [--trials 100] [--seed 1] [--confidence 0.85 0.99] [--known-rotations]

Each trial: a random 25-move scramble (engine, verified against RubikTwoPhase), six faces of readings in
random rotations, then misreads and unseen tiles injected. A reading puts `confidence` (uniform in the
given range) on its color and spreads the rest randomly; a misread does the same for a wrong color.
Outcomes: unique (and right) / WRONG (unique but not the scramble: must stay at zero) / corrected (right
after overriding confident readings) / mis-corr (corrected, wrong: why "corrected" is not final) /
deduced (incomplete, right) / mis-ded (incomplete, wrong) / ambiguous (scramble
listed) / truncated (too many candidates to list, scramble not among them) / unlisted (list complete but
the scramble is not in it: misreads made it too unlikely) / invalid. --known-rotations passes every
seen face's rotation, as when faces are seen next to a neighbor. Simulated readings are a development
aid, not evidence of real accuracy.
"""
from __future__ import annotations

import argparse
import random
import time

import numpy as np

from cubetrack.cube import SOLVED, apply_moves, state_to_facelets
from cubetrack.cube.facelets import CENTERS, FACES
from cubetrack.vision.assemble import STANDARD_SCHEME, assemble
from cubetrack.vision.color import COLORS

CONDITIONS = [  # name, misreads, unseen tiles, unseen faces
    ("clean", 0, 0, 0),
    ("1 misread", 1, 0, 0),
    ("2 misreads", 2, 0, 0),
    ("3 misreads", 3, 0, 0),
    ("4 unseen tiles", 0, 4, 0),
    ("1 face unseen", 0, 0, 1),
    ("1 face unseen + 1 misread", 1, 0, 1),
    ("2 faces unseen", 0, 0, 2),
]
OUTCOMES = ("unique", "WRONG", "corrected", "mis-corr", "deduced", "mis-ded", "ambiguous", "truncated", "unlisted",
            "invalid")
COLOR_OF = {label: color for color, label in STANDARD_SCHEME.items()}


def reading(color: str, confidence: float, rng: random.Random) -> dict[str, float]:
    rest = np.array([rng.random() for _ in range(5)])
    rest = rest / rest.sum() * (1 - confidence)
    return {color: confidence, **dict(zip([c for c in COLORS if c != color], map(float, rest)))}


def simulate(facelets: str, rng: random.Random, misreads=0, unseen_tiles=0, unseen_faces=0,
             confidence=(0.85, 0.99)) -> dict:
    """Readings of the cube `facelets`, each face turned a random number of quarter turns -> (readings, turns)."""
    tiles = [i for i in range(54) if i not in CENTERS]
    hidden_faces = rng.sample(range(6), unseen_faces)
    hidden = set(rng.sample(tiles, unseen_tiles))
    wrong = set(rng.sample([i for i in tiles if i not in hidden and i // 9 not in hidden_faces], misreads))
    out, turns = {}, {}
    for f in range(6):
        if f in hidden_faces:
            continue
        grid = []
        for i in range(9 * f, 9 * f + 9):
            true = COLOR_OF[facelets[i]]
            color = rng.choice([c for c in COLORS if c != true]) if i in wrong else true
            grid.append(None if i in hidden else reading(color, rng.uniform(*confidence), rng))
        turns[COLOR_OF[FACES[f]]] = k = rng.randrange(4)  # observed = standard view turned k quarter turns clockwise
        out[COLOR_OF[FACES[f]]] = [grid[3 * r + c] for r, c in _turned_positions(k)]
    return out, turns


def _turned_positions(k: int):
    """For each position of a grid turned k quarter turns clockwise, the (row, col) it came from."""
    pos = [(r, c) for r in range(3) for c in range(3)]
    for _ in range(k):  # one clockwise quarter turn: new (r, c) shows old (2 - c, r)
        pos = [pos[3 * (2 - c) + r] for r in range(3) for c in range(3)]
    return pos


def outcome(result, truth: str) -> str:
    right = bool(result.candidates) and result.candidates[0].facelets == truth
    if result.status == "unique":
        return "unique" if right else "WRONG"
    if result.status == "corrected":
        return "corrected" if right else "mis-corr"
    if result.status == "incomplete":
        return "deduced" if right else "mis-ded"
    if result.status == "ambiguous" and truth not in [c.facelets for c in result.candidates]:
        return "truncated" if result.truncated else "unlisted"
    return result.status


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--confidence", type=float, nargs=2, default=(0.85, 0.99))
    parser.add_argument("--known-rotations", action="store_true", help="pass the faces' rotations to assembly")
    args = parser.parse_args(argv)

    moves = [f + s for f in FACES for s in ("", "'", "2")]
    print(f"{'condition':26s}" + "".join(f"{o:>10s}" for o in OUTCOMES) + f"{'median ms':>10s}")
    for name, misreads, tiles, faces in CONDITIONS:
        rng = random.Random(args.seed)
        counts, times = dict.fromkeys(OUTCOMES, 0), []
        for _ in range(args.trials):
            truth = state_to_facelets(apply_moves(SOLVED, [rng.choice(moves) for _ in range(25)]))
            readings, turns = simulate(truth, rng, misreads, tiles, faces, tuple(args.confidence))
            start = time.perf_counter()
            result = assemble(readings, rotations=turns if args.known_rotations else None)
            times.append(1000 * (time.perf_counter() - start))
            counts[outcome(result, truth)] += 1
        print(f"{name:26s}" + "".join(f"{counts[o]:10d}" for o in OUTCOMES) + f"{np.median(times):10.0f}")


if __name__ == "__main__":
    main()
