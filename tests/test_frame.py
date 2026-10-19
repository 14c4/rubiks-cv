"""Whole-cube rotations. Expected face mappings are hand-derived from holding a cube:

x (like R): the front comes up, so the face now on top was the front.
y (like U): the right comes to the front.
z (like F): the left comes up.
"""
import pytest

from cubetrack.cube import SOLVED, apply_moves
from cubetrack.cube.frame import Frame, apply_notation

pytestmark = pytest.mark.foundation


@pytest.mark.parametrize("rotation,face,expected", [
    ("x", "U", "F"), ("x", "F", "D"), ("x", "R", "R"),
    ("y", "F", "R"), ("y", "R", "B"), ("y", "U", "U"),
    ("z", "U", "L"), ("z", "R", "U"), ("z", "F", "F"),
])
def test_hand_derived_face_after_rotation(rotation, face, expected):
    assert Frame().rotate(rotation)[face] == expected


@pytest.mark.parametrize("axis", "xyz")
def test_rotation_identities(axis):
    f = Frame()
    assert f.rotate(axis).rotate(axis).rotate(axis).rotate(axis) == f
    assert f.rotate(axis).rotate(axis + "'") == f
    assert f.rotate(axis + "2") == f.rotate(axis).rotate(axis)


def test_rotations_never_change_the_cubie_state():
    state, frame = apply_notation(SOLVED, Frame(), "x y z' y2 x'")
    assert state == SOLVED and frame != Frame()


@pytest.mark.parametrize("notation,intrinsic", [
    ("y F", "R"),  # after y the right face is in front
    ("x U", "F"),
    ("z U", "L"),
    ("y R y'", "B"),
    ("x R x'", "R"),
    ("y R U y' F", "B U F"),
])
def test_mixed_rotations_and_turns(notation, intrinsic):
    state, _ = apply_notation(SOLVED, Frame(), notation)
    assert state == apply_moves(SOLVED, intrinsic)


def test_unknown_tokens_are_rejected():
    with pytest.raises(ValueError, match="token 2"):
        apply_notation(SOLVED, Frame(), "R w")
