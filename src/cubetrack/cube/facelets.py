"""Facelets (the 54 sticker positions) and their conversion to and from the cubie state.

A facelet string has 54 characters in face order U R F D L B, nine per face, each face read row by
row as seen from outside (docs/conventions.md). Characters are face labels, not colors: the scanner
maps colors to labels through the centers. '?' marks an unknown sticker (an incomplete scan).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from cubetrack.cube.state import CubeState, physical_problems

FACES = "URFDLB"
UNKNOWN = "?"
SOLVED_FACELETS = "".join(f * 9 for f in FACES)


def idx(name: str) -> int:
    """'U1' -> 0, 'R1' -> 9, ... 'B9' -> 53."""
    return FACES.index(name[0]) * 9 + int(name[1]) - 1


# Slot -> facelets, starting with the U/D sticker then clockwise (corners); reference sticker first (edges).
CORNER_FACELETS = tuple(tuple(idx(n) for n in names.split()) for names in (
    "U9 R1 F3", "U7 F1 L3", "U1 L1 B3", "U3 B1 R3", "D3 F9 R7", "D1 L9 F7", "D7 B9 L7", "D9 R9 B7"))
EDGE_FACELETS = tuple(tuple(idx(n) for n in names.split()) for names in (
    "U6 R2", "U8 F2", "U4 L2", "U2 B2", "D6 R8", "D2 F8", "D4 L8", "D8 B8", "F6 R4", "F4 L6", "B6 L4", "B4 R6"))
# A piece's colors are the labels of its home slot in the solved cube, in the same order.
CORNER_COLORS = tuple(tuple(SOLVED_FACELETS[i] for i in slot) for slot in CORNER_FACELETS)
EDGE_COLORS = tuple(tuple(SOLVED_FACELETS[i] for i in slot) for slot in EDGE_FACELETS)
CENTERS = tuple(9 * f + 4 for f in range(6))


@dataclass
class Diagnostic:
    code: str  # stable identifier, e.g. "color_count", "invalid_corner", "parity"
    message: str
    facelets: tuple[int, ...] = ()  # implicated facelet indices, if any


@dataclass
class ValidationResult:
    status: str  # "valid", "invalid" or "incomplete"
    diagnostics: list[Diagnostic] = field(default_factory=list)
    state: CubeState | None = None  # set when the pieces could be identified

    @property
    def codes(self) -> list[str]:
        return [d.code for d in self.diagnostics]


def state_to_facelets(state: CubeState) -> str:
    f = list(SOLVED_FACELETS)  # centers stay as they are
    for i, (piece, ori) in enumerate(zip(state.cp, state.co)):
        for k in range(3):
            f[CORNER_FACELETS[i][(k + ori) % 3]] = CORNER_COLORS[piece][k]
    for i, (piece, ori) in enumerate(zip(state.ep, state.eo)):
        for k in range(2):
            f[EDGE_FACELETS[i][(k + ori) % 2]] = EDGE_COLORS[piece][k]
    return "".join(f)


def _identify_corner(colors):
    """(piece, twist) whose stickers read `colors` in this slot's order, or None (impossible or mirrored)."""
    for ori in range(3):
        if colors[ori] in "UD":
            rest = (colors[(ori + 1) % 3], colors[(ori + 2) % 3])
            for piece, pc in enumerate(CORNER_COLORS):
                if (pc[1], pc[2]) == rest and pc[0] == colors[ori]:
                    return piece, ori
    return None


def _identify_edge(colors):
    for piece, pc in enumerate(EDGE_COLORS):
        if tuple(colors) == pc:
            return piece, 0
        if tuple(colors) == pc[::-1]:
            return piece, 1
    return None


def validate_facelets(facelets: str) -> ValidationResult:
    """Check a facelet string against everything a real cube must satisfy.

    Order: malformed input, then unknown stickers (incomplete), then color counts and centers, then
    piece identification (impossible / mirrored / duplicate / missing pieces), then invariants.
    """
    if not isinstance(facelets, str) or len(facelets) != 54:
        n = len(facelets) if isinstance(facelets, str) else None
        return ValidationResult("invalid", [Diagnostic("malformed", f"need 54 characters, got {n}")])
    bad = tuple(i for i, ch in enumerate(facelets) if ch not in FACES + UNKNOWN)
    if bad:
        return ValidationResult("invalid", [Diagnostic("malformed", f"unexpected characters at {list(bad)}", bad)])

    diags = []
    counts = {f: facelets.count(f) for f in FACES}
    unknown = facelets.count(UNKNOWN)
    for f, n in counts.items():
        if n > 9 or (unknown == 0 and n != 9):
            diags.append(Diagnostic("color_count", f"{f} appears {n} times, expected 9",
                                    tuple(i for i, ch in enumerate(facelets) if ch == f)))
    for face, i in zip(FACES, CENTERS):
        if facelets[i] not in (face, UNKNOWN):
            diags.append(Diagnostic("center", f"center of {face} is {facelets[i]}", (i,)))
    if unknown:
        status = "invalid" if diags else "incomplete"
        return ValidationResult(status, diags + [Diagnostic("incomplete", f"{unknown} unknown stickers")])

    cp, co, ep, eo = [], [], [], []
    for slot in CORNER_FACELETS:
        found = _identify_corner([facelets[i] for i in slot])
        if found is None:
            diags.append(Diagnostic("invalid_corner", f"corner {''.join(facelets[i] for i in slot)} does not exist "
                                    "(impossible colors or mirrored order)", slot))
            found = (None, None)
        cp.append(found[0]), co.append(found[1])
    for slot in EDGE_FACELETS:
        found = _identify_edge([facelets[i] for i in slot])
        if found is None:
            diags.append(Diagnostic("invalid_edge", f"edge {''.join(facelets[i] for i in slot)} does not exist", slot))
            found = (None, None)
        ep.append(found[0]), eo.append(found[1])
    for kind, perm, n, slots in (("corner", cp, 8, CORNER_FACELETS), ("edge", ep, 12, EDGE_FACELETS)):
        for piece in range(n):
            where = [s for s, p in enumerate(perm) if p == piece]
            if len(where) > 1:
                diags.append(Diagnostic(f"duplicate_{kind}", f"{kind} piece {piece} appears {len(where)} times",
                                        tuple(i for s in where for i in slots[s])))
            elif not where:
                diags.append(Diagnostic(f"missing_{kind}", f"{kind} piece {piece} is missing"))
    if diags:
        return ValidationResult("invalid", diags)

    state = CubeState(tuple(cp), tuple(co), tuple(ep), tuple(eo))
    diags = [Diagnostic(code, msg) for code, msg in physical_problems(state)]
    return ValidationResult("invalid" if diags else "valid", diags, state)


class InvalidCube(ValueError):
    def __init__(self, result: ValidationResult):
        super().__init__("; ".join(f"{d.code}: {d.message}" for d in result.diagnostics))
        self.result = result


def facelets_to_state(facelets: str) -> CubeState:
    """The cubie state for a complete, physically valid facelet string; raises InvalidCube otherwise."""
    result = validate_facelets(facelets)
    if result.status != "valid":
        raise InvalidCube(result)
    return result.state
