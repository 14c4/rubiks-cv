"""Assembly (roadmap 2.5) checks on simulated inspection readings.

Expected cubes come from tests/fixtures/cube/reference_sequences.json (Kociemba's RubikTwoPhase, an
independent engine) and from hand-derived facelet strings; never from the code under test.
Readings are built here by hand: every tile reads its true color at 0.99 (0.002 on each other color)
unless a test says otherwise, and every face is turned by a random number of quarter turns.

Why a single misread is always correctable: two different legal cubes differ in at least 3 tiles, so
with equally confident tiles the true cube (1 tile off) is strictly closer than any other (>= 2 off).
"""
import json
import random
from pathlib import Path

import pytest

from cubetrack.cube import SOLVED_FACELETS, validate_facelets
from cubetrack.cube.facelets import idx
from cubetrack.vision.assemble import assemble

REFERENCE = json.loads((Path(__file__).parent / "fixtures" / "cube" / "reference_sequences.json").read_text())
CASES = REFERENCE["cases"]
RANDOM_CASES = CASES[24:]  # the 50 seeded random sequences
SINGLE_MOVES = CASES[:18]
COLOR = {"U": "white", "R": "red", "F": "green", "D": "yellow", "L": "orange", "B": "blue"}  # D-004
SEED = 20261018


def tile(color, p=0.99, second=None, q=0.0):
    """A reading: `color` at p, optionally `second` at q, the rest shared equally."""
    rest = [c for c in COLOR.values() if c not in (color, second)]
    out = {c: (1 - p - q) / len(rest) for c in rest}
    out[color] = p
    if second:
        out[second] = q
    return out


def turn_clockwise(grid):
    """A 3x3 grid (row by row) turned a quarter turn clockwise: the top row becomes the right column."""
    return [grid[3 * (2 - c) + r] for r in range(3) for c in range(3)]


def readings(facelets, rng, override=None, hidden=(), hidden_faces=""):
    """Readings of the cube `facelets`; returns (readings, quarter turns applied to each face)."""
    override = override or {}
    out, turns = {}, {}
    for f, label in enumerate("URFDLB"):
        if label in hidden_faces:
            continue
        grid = [None if i in hidden else override.get(i, tile(COLOR[facelets[i]])) for i in range(9 * f, 9 * f + 9)]
        turns[COLOR[label]] = k = rng.randrange(4)
        for _ in range(k):
            grid = turn_clockwise(grid)
        out[COLOR[label]] = grid
    return out, turns


def faces_match_up_to_turns(a, b):
    for f in range(6):
        grid, target = list(a[9 * f:9 * f + 9]), list(b[9 * f:9 * f + 9])
        turned = [grid]
        for _ in range(3):
            turned.append(turn_clockwise(turned[-1]))
        if target not in turned:
            return False
    return True


def names(*facelet_names):
    return tuple(sorted(idx(n) for n in facelet_names))


# ---------- clean readings ----------

@pytest.mark.parametrize("case", SINGLE_MOVES + RANDOM_CASES[:10] + [{"sequence": "", "facelets": SOLVED_FACELETS}],
                         ids=lambda c: c["sequence"][:30] or "solved")
def test_clean_readings_with_known_rotations_give_exactly_that_cube(case):
    # Every tile is pinned down, and any other legal cube contradicts at least 3 confident tiles.
    given, turns = readings(case["facelets"], random.Random(SEED))
    result = assemble(given, rotations=turns)
    assert result.status == "unique", result.message
    assert [c.facelets for c in result.candidates] == [case["facelets"]]
    assert result.best.corrected == result.best.contradicted == result.best.inferred == ()
    assert result.raw.status == "valid"


@pytest.mark.parametrize("case", RANDOM_CASES, ids=lambda c: c["sequence"][:30])
def test_clean_readings_of_scrambles(case):
    truth = case["facelets"]
    result = assemble(readings(truth, random.Random(SEED))[0])
    # The scramble fits every tile, so nothing beats it. Any other listed cube must fit every tile too
    # (one contradicted 0.99 tile costs more than the margin): a real "face turned differently" twin.
    listed = [c for c in result.candidates if c.facelets == truth]
    assert listed and listed[0].log_likelihood == pytest.approx(result.best.log_likelihood)
    for c in result.candidates:
        assert validate_facelets(c.facelets).status == "valid"
        assert faces_match_up_to_turns(c.facelets, truth)
    assert result.status == ("unique" if len(result.candidates) == 1 else "ambiguous")


def test_u_and_d_prime_look_alike_without_known_rotations():
    # After U the side faces' top rows have moved one face along; after D' their bottom rows have, the
    # same way round. Turning each side face 180 degrees turns one picture into the other, so with face
    # rotations unknown both cubes fit every tile. Knowing the side faces' rotations settles it.
    u, d_prime = (next(c["facelets"] for c in CASES if c["sequence"] == m) for m in ("U", "D'"))
    given, turns = readings(u, random.Random(SEED))
    result = assemble(given)
    assert result.status == "ambiguous"
    assert sorted(c.facelets for c in result.candidates) == sorted([u, d_prime])
    sides = {COLOR[f]: turns[COLOR[f]] for f in "RFLB"}
    assert [c.facelets for c in assemble(given, rotations=sides).candidates] == [u]


def test_reported_rotations_are_the_turns_applied():
    truth = next(c["facelets"] for c in CASES if c["sequence"] == "L' D2 B R F' U L2 B' D")
    given, turns = readings(truth, random.Random(SEED))
    result = assemble(given)
    assert result.status == "unique"
    for f, label in enumerate("URFDLB"):
        face = list(truth[9 * f:9 * f + 9])
        if turn_clockwise(face) != face and turn_clockwise(turn_clockwise(face)) != face:  # rotation visible
            assert result.best.rotations[COLOR[label]] == turns[COLOR[label]], label


# ---------- misreads ----------

@pytest.mark.parametrize("case", RANDOM_CASES[:20], ids=lambda c: c["sequence"][:30])
def test_one_confident_misread_is_corrected_and_reported(case):
    truth = case["facelets"]
    rng = random.Random(SEED)
    i = rng.choice([i for i in range(54) if i % 9 != 4])
    wrong = rng.choice([c for c in COLOR.values() if c != COLOR[truth[i]]])
    given, turns = readings(truth, rng, override={i: tile(wrong)})
    result = assemble(given, rotations=turns)  # so the misread's position is defined even on a one-color face
    listed = [c for c in result.candidates if c.facelets == truth]
    assert listed, result.message
    scramble = listed[0]
    assert scramble.log_likelihood == pytest.approx(result.best.log_likelihood)
    assert scramble.corrected == scramble.contradicted == (i,)
    assert result.status in ("corrected", "ambiguous")  # never "unique": a confident reading was overridden
    assert result.raw.status == "invalid"  # the readings alone break the nine-per-color count


def test_uncertain_tiles_are_settled_by_the_pieces():
    # Solved cube; three corner stickers lean towards the wrong color (0.55) over the right one (0.40).
    # One changed sticker never makes a real corner, so any other cube must change confident tiles too.
    # (Rotations given: on a one-color face nothing else tells where the leaning tile sits.)
    lean = {idx("U1"): tile("yellow", 0.55, "white", 0.40), idx("F9"): tile("blue", 0.55, "green", 0.40),
            idx("R3"): tile("orange", 0.55, "red", 0.40)}
    given, turns = readings(SOLVED_FACELETS, random.Random(SEED), override=lean)
    result = assemble(given, rotations=turns)
    assert result.status == "unique", result.message
    assert result.best.facelets == SOLVED_FACELETS
    assert result.best.corrected == names("U1", "F9", "R3")
    assert result.best.contradicted == ()


def test_twisted_corner_is_invalid():
    # Solved, but the URF corner twisted clockwise in place: U9 shows F, R1 shows U, F3 shows R.
    # Every legal cube is at least 3 tiles away (untwist it, or twist another corner), all confident.
    twisted = list(SOLVED_FACELETS)
    twisted[idx("U9")], twisted[idx("R1")], twisted[idx("F3")] = "F", "U", "R"
    result = assemble(readings("".join(twisted), random.Random(SEED))[0])
    assert result.status == "invalid", result.message
    assert len(result.best.contradicted) >= 3
    assert "corner_twist" in result.raw.codes


# ---------- unseen tiles ----------

def test_hidden_edge_pair_is_ambiguous_and_names_the_tiles():
    # Solved with U6 R2 (edge UR) and U8 F2 (edge UF) unseen. Both edges flipped is also a legal cube
    # (flips stay even); swapping them is not (a single swap breaks parity). So exactly two cubes fit.
    # (Rotations given: on one-color faces, unknown rotations would move the holes onto other edges.)
    hidden = names("U6", "R2", "U8", "F2")
    flipped = list(SOLVED_FACELETS)
    flipped[idx("U6")], flipped[idx("R2")], flipped[idx("U8")], flipped[idx("F2")] = "R", "U", "F", "U"
    given, turns = readings(SOLVED_FACELETS, random.Random(SEED), hidden=hidden)
    result = assemble(given, rotations=turns)
    assert result.status == "ambiguous"
    assert sorted(c.facelets for c in result.candidates) == sorted([SOLVED_FACELETS, "".join(flipped)])
    assert result.disputed == hidden
    assert not result.truncated


def test_unseen_face_of_solved_cube_is_deduced():
    # D unseen: every D corner shows two stickers (which fixes the piece), every D edge shows its side
    # sticker and only the yellow-<side> piece is left for it. One cube, but deduced, not seen.
    result = assemble(readings(SOLVED_FACELETS, random.Random(SEED), hidden_faces="D")[0])
    assert result.status == "incomplete", result.message
    assert [c.facelets for c in result.candidates] == [SOLVED_FACELETS]
    assert result.best.inferred == names("D1", "D2", "D3", "D4", "D6", "D7", "D8", "D9")
    assert result.raw.status == "incomplete"


def test_all_unknown_reading_counts_as_unseen():
    given, turns = readings(SOLVED_FACELETS, random.Random(SEED), override={idx("D2"): {"unknown": 1.0}})
    result = assemble(given, rotations=turns)
    assert result.status == "incomplete"
    assert result.best.facelets == SOLVED_FACELETS
    assert result.best.inferred == names("D2")


@pytest.mark.parametrize("case", RANDOM_CASES[:20], ids=lambda c: c["sequence"][:30])
def test_one_unseen_face_of_scrambles(case):
    # The scramble fits every seen tile, so nothing fits better: it is listed (unless the list is cut
    # short), and a single deduced answer can only be the scramble.
    truth = case["facelets"]
    rng = random.Random(SEED)
    result = assemble(readings(truth, rng, hidden_faces=rng.choice("URFDLB"))[0])
    assert result.status in ("incomplete", "ambiguous")
    assert result.truncated or truth in [c.facelets for c in result.candidates]
    if result.status == "incomplete":
        assert result.best.facelets == truth
        assert len(result.best.inferred) == 8


def test_no_readings_at_all():
    result = assemble({})
    assert result.status == "ambiguous" and result.truncated


# ---------- input checks ----------

@pytest.mark.parametrize("bad, message", [
    ({"purple": [None] * 9}, "named by center color"),
    ({"white": [None] * 8}, "9 tile readings"),
    ({"white": [{"white": 1.5}] + [None] * 8}, "0..1"),
    ({"white": [{"pink": 0.5}] + [None] * 8}, "unknown colors"),
    ({"white": ["white"] + [None] * 8}, "dict of probabilities"),
])
def test_malformed_readings_are_rejected(bad, message):
    with pytest.raises(ValueError, match=message):
        assemble(bad)


@pytest.mark.parametrize("rotations", [{"purple": 0}, {"white": 4}])
def test_malformed_rotations_are_rejected(rotations):
    with pytest.raises(ValueError, match="quarter turns"):
        assemble({}, rotations=rotations)
