"""The 18 face turns, derived from 3D geometry rather than typed-in tables, and move-sequence parsing.

Each facelet gets a position (the cubie it sits on, coordinates in {-1, 0, 1}) and an outward normal.
Axes: x toward R, y toward U, z toward F. A clockwise turn of a face (as seen from outside that face)
rotates every facelet of that layer by -90 degrees about the face's outward normal. Tracking where
each facelet goes gives the move as a facelet permutation; converting the turned solved cube to
cubies gives the move as a CubeState.
"""
from __future__ import annotations

import re

from cubetrack.cube.facelets import FACES, SOLVED_FACELETS, facelets_to_state
from cubetrack.cube.state import SOLVED, CubeState

NORMALS = {"U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1), "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1)}


def _facelet_position(face: str, row: int, col: int) -> tuple[int, int, int]:
    """Cubie position of a facelet, from the viewing directions in docs/conventions.md."""
    return {
        "U": (col - 1, 1, row - 1),  # seen from above, B at the top
        "R": (1, 1 - row, 1 - col),  # seen from the right, U at the top, F on the left
        "F": (col - 1, 1 - row, 1),
        "D": (col - 1, -1, 1 - row),  # seen from below, F at the top
        "L": (-1, 1 - row, col - 1),
        "B": (1 - col, 1 - row, -1),  # seen from behind, R on the left
    }[face]


GEOMETRY = [(_facelet_position(f, i // 3, i % 3), NORMALS[f]) for f in FACES for i in range(9)]
_INDEX = {g: i for i, g in enumerate(GEOMETRY)}


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _rotate_cw(v, axis):
    """Rotate v by -90 degrees about the unit axis (Rodrigues' formula with cos = 0, sin = -1)."""
    c = _cross(axis, v)
    d = sum(a * b for a, b in zip(axis, v))
    return tuple(-c[k] + d * axis[k] for k in range(3))


def facelet_permutation(face: str) -> list[int]:
    """perm[dest] = src: after a clockwise turn of `face`, the sticker at dest came from src."""
    axis = NORMALS[face]
    perm = list(range(54))
    for src, (pos, normal) in enumerate(GEOMETRY):
        if sum(a * b for a, b in zip(pos, axis)) == 1:  # facelet lies on the turning layer
            perm[_INDEX[(_rotate_cw(pos, axis), _rotate_cw(normal, axis))]] = src
    return perm


def _basic_move(face: str) -> CubeState:
    perm = facelet_permutation(face)
    return facelets_to_state("".join(SOLVED_FACELETS[perm[i]] for i in range(54)))


MOVES: dict[str, CubeState] = {}
for _f in FACES:
    _q = _basic_move(_f)
    MOVES[_f], MOVES[_f + "2"], MOVES[_f + "'"] = _q, _q * _q, _q * _q * _q

_TOKEN = re.compile(r"^[URFDLB](2|')?$")


def parse_moves(text: str) -> list[str]:
    """'R U2 F'' -> ['R', 'U2', "F'"]. Rejects anything outside the 18 face turns with the reason."""
    tokens = text.split()
    for pos, tok in enumerate(tokens):
        if _TOKEN.match(tok):
            continue
        if re.match(r"^[URFDLB](2'|'2)$", tok):
            hint = f"write {tok[0]}2 (a half turn has no direction)"
        elif re.match(r"^([urfdlb]|[URFDLB]w|[MESxyz])", tok):
            hint = "wide, slice and rotation moves are not supported yet"
        else:
            hint = "expected a face U R F D L B, optionally followed by 2 or '"
        raise ValueError(f"move {pos + 1} {tok!r}: {hint}")
    return tokens


def invert_sequence(moves: list[str]) -> list[str]:
    """Reverse the order and invert each move: (R U') -> (U R')."""
    inv = {"": "'", "'": "", "2": "2"}
    return [m[0] + inv[m[1:]] for m in reversed(moves)]


def apply_moves(state: CubeState, moves: str | list[str] = "") -> CubeState:
    for m in parse_moves(moves) if isinstance(moves, str) else moves:
        state = state * MOVES[m]
    return state


def scramble_state(moves: str) -> CubeState:
    return apply_moves(SOLVED, moves)
