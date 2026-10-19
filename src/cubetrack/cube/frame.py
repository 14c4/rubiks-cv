"""Whole-cube rotations x, y, z as a change of reference frame (D-002).

The cubie state lives in a fixed intrinsic frame and is never edited by a rotation. A Frame records
which intrinsic face currently sits in each notation position (what the solver calls U, R, F, ...).
Turning notation "R" after a "y" therefore turns whichever intrinsic face is now on the right.

x follows R, y follows U, z follows F (clockwise as seen from that face), the standard direction.
Pose tracking will update the frame; it must never change the cubie state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from cubetrack.cube.moves import MOVES, NORMALS, _rotate_cw
from cubetrack.cube.state import CubeState

AXIS_FACE = {"x": "R", "y": "U", "z": "F"}
_FACE_OF_NORMAL = {n: f for f, n in NORMALS.items()}
_TOKEN = re.compile(r"^([URFDLB]|[xyz])(2|')?$")


@dataclass(frozen=True)
class Frame:
    """mapping[notation face] = intrinsic face. Identity: each face is itself."""

    mapping: tuple[tuple[str, str], ...] = tuple((f, f) for f in "URFDLB")

    def __getitem__(self, face: str) -> str:
        return dict(self.mapping)[face]

    def rotate(self, token: str) -> Frame:
        """Apply x, x', x2, y, ... to the frame."""
        axis, suffix = token[0], token[1:]
        turns = {"": 1, "2": 2, "'": 3}[suffix]
        current = dict(self.mapping)
        for _ in range(turns):
            n_axis = NORMALS[AXIS_FACE[axis]]
            nxt = {}
            for face, normal in NORMALS.items():
                # the face now at `normal` is the one that was at the position rotating onto it
                came_from = _rotate_cw(_rotate_cw(_rotate_cw(normal, n_axis), n_axis), n_axis)  # +90 degrees
                nxt[face] = current[_FACE_OF_NORMAL[came_from]]
            current = nxt
        return Frame(tuple((f, current[f]) for f in "URFDLB"))

    def to_intrinsic(self, move: str) -> str:
        """Notation face turn -> the intrinsic face turn it means in this frame."""
        return self[move[0]] + move[1:]


def apply_notation(state: CubeState, frame: Frame, text: str) -> tuple[CubeState, Frame]:
    """Apply face turns and rotations; rotations change only the frame."""
    for pos, tok in enumerate(text.split()):
        m = _TOKEN.match(tok)
        if not m:
            raise ValueError(f"token {pos + 1} {tok!r}: expected U R F D L B or x y z, optionally with 2 or '")
        if tok[0] in AXIS_FACE:
            frame = frame.rotate(tok)
        else:
            state = state * MOVES[frame.to_intrinsic(tok)]
    return state, frame
