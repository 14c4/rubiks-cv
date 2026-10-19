"""Regenerate reference_sequences.json with an INDEPENDENT engine: Kociemba's RubikTwoPhase package.

    pip install RubikTwoPhase==1.1.1
    python tests/fixtures/cube/generate_reference.py

Not used by the tests at run time; the JSON it writes is the stored expectation. Nothing from
cubetrack is imported here, so the fixtures cannot inherit a bug from the code they check.
"""
import json
import random
from pathlib import Path

import twophase.cubie as cubie

FACES = "URFDLB"
SUFFIX = {"": 0, "2": 1, "'": 2}  # twophase: moveCube[3 * face + k], k = 0 quarter, 1 half, 2 inverse


def apply(seq: str) -> str:
    cc = cubie.CubieCube()
    for tok in seq.split():
        cc.multiply(cubie.moveCube[3 * FACES.index(tok[0]) + SUFFIX[tok[1:]]])
    return cc.to_facelet_cube().to_string()


def main():
    moves = [f + s for f in FACES for s in ("", "'", "2")]
    named = ["R U F' L2 D B'", "R U R' U'", "R U", "U R", "F2 B2 L R' D U2", "L' D2 B R F' U L2 B' D"]
    rng = random.Random(20261018)  # fixed, documented seed
    randoms = [" ".join(rng.choice(moves) for _ in range(rng.randint(1, 30))) for _ in range(50)]
    cases = [{"sequence": s, "facelets": apply(s)} for s in moves + named + randoms]
    out = {
        "source": "RubikTwoPhase 1.1.1 (twophase.cubie.moveCube), generated 2026-10-18 by this script",
        "seed": 20261018,
        "layout": "Kociemba facelet string, face order U R F D L B (docs/conventions.md)",
        "cases": cases,
    }
    Path(__file__).with_name("reference_sequences.json").write_text(json.dumps(out, indent=1))
    print(f"wrote {len(cases)} cases")


if __name__ == "__main__":
    main()
