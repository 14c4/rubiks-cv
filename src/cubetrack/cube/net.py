"""Text six-face net for comparing the engine with a physical cube.

    python -m cubetrack.cube.net "R U R' U'"        # net after a sequence from solved
"""
from __future__ import annotations

import sys

from cubetrack.cube.facelets import FACES, state_to_facelets
from cubetrack.cube.moves import apply_moves
from cubetrack.cube.state import SOLVED, CubeState


def net(facelets: str) -> str:
    """Layout of docs/conventions.md: U on top, L F R B in a row, D below."""
    face = {f: facelets[9 * i:9 * i + 9] for i, f in enumerate(FACES)}

    def row(f, r):
        return " ".join(face[f][3 * r:3 * r + 3])

    lines = [" " * 8 + row("U", r) for r in range(3)]
    lines += ["  ".join(row(f, r) for f in "LFRB") for r in range(3)]
    lines += [" " * 8 + row("D", r) for r in range(3)]
    return "\n".join(lines)


def state_net(state: CubeState) -> str:
    return net(state_to_facelets(state))


if __name__ == "__main__":
    seq = " ".join(sys.argv[1:])
    print(state_net(apply_moves(SOLVED, seq)))
