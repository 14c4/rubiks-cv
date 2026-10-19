"""The authoritative cube state: which piece sits in each slot, and how it is twisted or flipped.

Pieces never change color; a state only says where each of the 8 corners and 12 edges is and how
it is oriented. Centers are fixed in this intrinsic frame (whole-cube rotations live elsewhere).

Composition ("apply A, then B"), Kociemba's "is replaced by" convention (docs/conventions.md):
    (A*B).cp[i] = A.cp[B.cp[i]]        (A*B).co[i] = (A.co[B.cp[i]] + B.co[i]) % 3
and the same for edges with % 2. Applying move M to state S gives S * M.
"""
from __future__ import annotations

from dataclasses import dataclass

FORMAT_VERSION = 1
N_CORNERS, N_EDGES = 8, 12


@dataclass(frozen=True)
class CubeState:
    cp: tuple[int, ...] = tuple(range(N_CORNERS))  # corner piece in each corner slot
    co: tuple[int, ...] = (0,) * N_CORNERS  # corner twist 0, 1, 2 (clockwise)
    ep: tuple[int, ...] = tuple(range(N_EDGES))  # edge piece in each edge slot
    eo: tuple[int, ...] = (0,) * N_EDGES  # edge flip 0, 1

    def __post_init__(self):
        problems = shape_problems(self.cp, self.co, self.ep, self.eo)
        if problems:
            raise ValueError("; ".join(problems))

    def __mul__(self, other: CubeState) -> CubeState:
        """self, then other."""
        cp = tuple(self.cp[other.cp[i]] for i in range(N_CORNERS))
        co = tuple((self.co[other.cp[i]] + other.co[i]) % 3 for i in range(N_CORNERS))
        ep = tuple(self.ep[other.ep[i]] for i in range(N_EDGES))
        eo = tuple((self.eo[other.ep[i]] + other.eo[i]) % 2 for i in range(N_EDGES))
        return CubeState(cp, co, ep, eo)

    def inverse(self) -> CubeState:
        """The state X with self * X == solved."""
        cp, co, ep, eo = [0] * N_CORNERS, [0] * N_CORNERS, [0] * N_EDGES, [0] * N_EDGES
        for i, piece in enumerate(self.cp):
            cp[piece] = i
            co[piece] = (-self.co[i]) % 3
        for i, piece in enumerate(self.ep):
            ep[piece] = i
            eo[piece] = self.eo[i]
        return CubeState(tuple(cp), tuple(co), tuple(ep), tuple(eo))

    def is_solved(self) -> bool:
        return self == SOLVED

    def to_dict(self) -> dict:
        return {"version": FORMAT_VERSION, "cp": list(self.cp), "co": list(self.co),
                "ep": list(self.ep), "eo": list(self.eo)}

    @classmethod
    def from_dict(cls, data: dict) -> CubeState:
        if data.get("version") != FORMAT_VERSION:
            raise ValueError(f"unsupported cube state version {data.get('version')!r} (expected {FORMAT_VERSION})")
        return cls(tuple(data["cp"]), tuple(data["co"]), tuple(data["ep"]), tuple(data["eo"]))


def shape_problems(cp, co, ep, eo) -> list[str]:
    """Structural errors that make the arrays meaningless (not physical-validity checks)."""
    problems = []
    for name, arr, size, values in (("cp", cp, N_CORNERS, None), ("co", co, N_CORNERS, 3),
                                    ("ep", ep, N_EDGES, None), ("eo", eo, N_EDGES, 2)):
        if len(arr) != size:
            problems.append(f"{name} has {len(arr)} entries, expected {size}")
        elif not all(isinstance(v, int) for v in arr):
            problems.append(f"{name} must contain integers")
        elif values is None and sorted(arr) != list(range(size)):
            problems.append(f"{name} must contain each of 0..{size - 1} exactly once (duplicate or missing piece)")
        elif values is not None and not all(0 <= v < values for v in arr):
            problems.append(f"{name} values must be in 0..{values - 1}")
    return problems


def permutation_parity(perm) -> int:
    """0 for an even permutation, 1 for odd (number of swaps needed, mod 2)."""
    seen, parity = [False] * len(perm), 0
    for start in range(len(perm)):
        length, i = 0, start
        while not seen[i]:
            seen[i] = True
            i = perm[i]
            length += 1
        if length:
            parity ^= (length - 1) & 1
    return parity


def physical_problems(state: CubeState) -> list[tuple[str, str]]:
    """(code, message) for every invariant a real cube must satisfy but this state breaks."""
    problems = []
    if sum(state.co) % 3:
        problems.append(("corner_twist", f"corner twists sum to {sum(state.co)}, not a multiple of 3"))
    if sum(state.eo) % 2:
        problems.append(("edge_flip", f"edge flips sum to {sum(state.eo)}, not even"))
    if permutation_parity(state.cp) != permutation_parity(state.ep):
        problems.append(("parity", "corner and edge permutation parities differ (a single swap of two pieces)"))
    return problems


SOLVED = CubeState()
