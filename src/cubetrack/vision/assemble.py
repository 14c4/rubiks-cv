"""Assembly (roadmap 2.5): six faces of tile color readings -> the legal cube state(s) that fit best.

Input: for each face seen, named by its center color, nine tile readings in reading order (row by row),
each a {color: probability} dict (e.g. `ColorEstimate.probabilities`; an "unknown" share is spread
evenly over the six colors) or None when the tile was not seen. Each face may be turned by an
unknown number of quarter turns. The center reading is ignored: the face is named by it.

How it works:
  1. Every reading becomes a cost per color: -ln P(reading | tile really is that color). A small
     `misread_rate` is mixed in, so a confident wrong reading makes a cube unlikely, not impossible.
     Unseen tiles cost nothing for any color.
  2. A cube is chosen piece by piece, not tile by tile: every corner slot gets one of the 8 corner
     pieces in one of 3 twists, every edge slot one of the 12 edge pieces in one of 2 flips, each
     piece used once, twists summing to a multiple of 3, flips even, corner and edge permutation
     parities equal. A cube's cost is the sum of its tiles' costs. Using each piece once makes the
     nine-tiles-per-color rule hold automatically, and is stricter than counting colors.
  3. The face rotations (4^6 = 4096 combinations) are searched too. For each combination a cheap lower
     bound (every slot takes its cheapest piece, repeats allowed) is computed for all combinations at
     once; a wrong rotation tears pieces apart (a corner made of three unrelated stickers), so its
     bound is high and it is skipped.
  4. Branch and bound finds the cheapest legal cube, then every legal cube within `margin` of it
     (a likelihood ratio of e^margin). The engine (cube/facelets.py) validates the raw readings.

Face rotations that are not known make some cubes indistinguishable: the cube after U and the cube
after D' read the same once each side face is turned 180 degrees. Seeing a face next to a neighbor
fixes its rotation (white's edge touching green is U's bottom row); pass such faces in `rotations`.

MARGIN (ln 100) is below the cost of one contradiction by a confident reading (about 5.2 at 0.99,
at most ln(6 / misread_rate) = 5.7), so a single confident misread is corrected outright; readings
below about 0.97 confidence leave such a case ambiguous instead.

Result status (only "unique" is a confirmed reading):
  unique      one cube fits clearly better than any other, every tile was seen and agrees with it
  corrected   one cube fits clearly best, but it overrides 1..max_contradicted confident readings;
              look at those tiles again (`best.contradicted`)
  incomplete  one cube fits, but some tiles were never seen and were deduced from the pieces
  ambiguous   several cubes fit about equally well; `disputed` lists the tiles that would decide
  invalid     no legal cube fits without overriding more than `max_contradicted` confident readings
The constraint-corrected result (`candidates`) and the raw readings (`raw`) are kept separate.

Two different legal cubes can differ in as few as 3 tiles (three edges cycled around one face), so one
misread is always correctable, but two or three confident misreads can make another legal cube fit
best. That cube then still contradicts a confident reading, which is why "corrected" is not "unique".
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np

from cubetrack.cube.facelets import (CENTERS, CORNER_COLORS, CORNER_FACELETS, EDGE_COLORS, EDGE_FACELETS, FACES,
                                     UNKNOWN, ValidationResult, state_to_facelets, validate_facelets)
from cubetrack.cube.state import CubeState, permutation_parity
from cubetrack.vision.color import COLORS

STANDARD_SCHEME = {"white": "U", "red": "R", "green": "F", "yellow": "D", "orange": "L", "blue": "B"}  # D-004

MISREAD_RATE = 0.02  # chance a reading has nothing to do with the true color
MARGIN = math.log(100)  # cubes within this log-likelihood of the best count as competitors (100x less likely)
CONTRADICTION = 0.1  # a reading that gave the chosen color less than this probability "contradicts" it
MAX_CONTRADICTED = 2  # more contradicted tiles than this -> invalid (rescan)
MAX_CANDIDATES = 10
MAX_NODES = 2_000_000  # search budget; exceeding it reports the result as truncated
_EPS = 1e-9


@dataclass(frozen=True)
class Candidate:
    state: CubeState
    facelets: str
    log_likelihood: float  # sum over seen tiles of ln P(reading | this cube), misread rate included
    rotations: dict[str, int]  # face color -> clockwise quarter turns of the reading from the standard view
    corrected: tuple[int, ...]  # seen facelets whose most likely reading is not this cube's color
    contradicted: tuple[int, ...]  # of those, the ones whose reading gave this cube's color < CONTRADICTION
    inferred: tuple[int, ...]  # facelets never seen, filled in from the pieces


@dataclass
class AssemblyResult:
    status: str  # "unique", "corrected", "incomplete", "ambiguous" or "invalid"
    candidates: list[Candidate]  # best first
    raw: ValidationResult  # engine verdict on the readings alone ('?' where unseen), best candidate's rotations
    disputed: tuple[int, ...]  # facelets on which the candidates disagree: the tiles to look at again
    truncated: bool  # more candidates than MAX_CANDIDATES, or the search budget ran out
    message: str

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None


def facelet_name(i: int) -> str:
    """0 -> 'U1', 53 -> 'B9'."""
    return f"{FACES[i // 9]}{i % 9 + 1}"


# Index tables for turning per-facelet costs into per-(slot, piece, orientation) costs.
# A piece with orientation o in slot s puts its k-th color on facelet slot[(k + o) % n] (state_to_facelets).
def _tables(slots, colors):
    n = len(slots[0])
    where = np.array([[[slot[(k + o) % n] for k in range(n)] for o in range(n)] for slot in slots])  # (slot, o, k)
    what = np.array([[FACES.index(c) for c in piece] for piece in colors])  # (piece, k)
    return where[:, None, :, :], what[None, :, None, :]


_CORNER_IDX = _tables(CORNER_FACELETS, CORNER_COLORS)
_EDGE_IDX = _tables(EDGE_FACELETS, EDGE_COLORS)


def _piece_costs(cost54, idx):
    """(..., 54, 6) facelet costs -> (..., slot, piece, orientation) costs."""
    where, what = idx
    return cost54[..., where, what].sum(axis=-1)


class _OutOfBudget(Exception):
    pass


class _Search:
    """Branch and bound over legal cubes for one rotation combination.

    `cubes(limit)` yields every legal cube with cost <= limit() as (cost, cp, co, ep, eo). `limit` is
    called again at every step, so a caller looking for the best cube can lower it as it goes.
    """

    def __init__(self, corner_costs, edge_costs, budget):
        self.cc, self.ec, self.budget = corner_costs, edge_costs, budget
        self.edge_floor = float(edge_costs.min(axis=(1, 2)).sum())

    def _assign(self, costs, limit):
        n, _, m = costs.shape
        cheapest = costs.min(axis=2)  # (slot, piece): best orientation of that piece in that slot
        options = [sorted((float(costs[s, p, o]), p, o) for p in range(n) for o in range(m)) for s in range(n)]
        used = np.zeros(n, dtype=bool)
        perm, ori = [], []

        def step(s, cost):
            self.budget[0] -= 1
            if self.budget[0] < 0:
                raise _OutOfBudget
            if s == n:
                yield cost, tuple(perm), tuple(ori)
                return
            # Lower bound: each remaining slot takes its cheapest unused piece (repeats allowed).
            if cost + float(cheapest[s:][:, ~used].min(axis=1).sum()) > limit() + _EPS:
                return
            forced = (-sum(ori)) % m if s == n - 1 else None  # the last twist/flip makes the sum legal
            for c, p, o in options[s]:
                if cost + c > limit() + _EPS:
                    break  # options are sorted, the rest are worse
                if used[p] or (forced is not None and o != forced):
                    continue
                used[p] = True
                perm.append(p), ori.append(o)
                yield from step(s + 1, cost + c)
                used[p] = False
                perm.pop(), ori.pop()

        yield from step(0, 0.0)

    def cubes(self, limit):
        for c_cost, cp, co in self._assign(self.cc, lambda: limit() - self.edge_floor):
            parity = permutation_parity(cp)
            for e_cost, ep, eo in self._assign(self.ec, lambda: limit() - c_cost):
                if permutation_parity(ep) == parity:
                    yield c_cost + e_cost, cp, co, ep, eo


def _tile_probs(tile, scheme):
    """A reading -> probabilities over face labels (FACES order), or None if it carries no color information."""
    if tile is None:
        return None
    if not isinstance(tile, dict):
        raise ValueError(f"a tile reading must be a dict of probabilities or None, got {type(tile).__name__}")
    extra = set(tile) - set(COLORS) - {"unknown"}
    if extra:
        raise ValueError(f"unknown colors in reading: {sorted(extra)}")
    if any(not 0 <= v <= 1 + 1e-6 for v in tile.values()):
        raise ValueError(f"probabilities must lie in 0..1: {tile}")
    p = np.zeros(6)
    for color in COLORS:
        p[FACES.index(scheme[color])] = tile.get(color, 0.0)
    if p.sum() <= 0:
        return None  # all "unknown": no evidence at all
    p += tile.get("unknown", 0.0) / 6  # an "unknown" share says nothing about which color
    return p / p.sum()


def _parse(readings, scheme):
    """-> {face index: (9, 6) probabilities with NaN rows for unseen tiles}."""
    if sorted(scheme) != sorted(COLORS) or sorted(scheme.values()) != sorted(FACES):
        raise ValueError(f"scheme must map the six colors {COLORS} one-to-one onto {FACES}")
    faces = {}
    for color, tiles in readings.items():
        if color not in scheme:
            raise ValueError(f"faces are named by center color, one of {COLORS}; got {color!r}")
        if len(tiles) != 9:
            raise ValueError(f"face {color} needs 9 tile readings in reading order, got {len(tiles)}")
        probs = np.full((9, 6), np.nan)
        for t, tile in enumerate(tiles):
            if t != 4:  # the center names the face; its reading is not evidence about anything else
                p = _tile_probs(tile, scheme)
                if p is not None:
                    probs[t] = p
        if not np.isnan(probs).all():
            faces[FACES.index(scheme[color])] = probs
    return faces


def _parse_rotations(rotations, scheme):
    known = {}
    for color, k in rotations.items():
        if color not in scheme or k not in range(4):
            raise ValueError(f"rotations map a center color to 0..3 quarter turns; got {color!r}: {k!r}")
        known[FACES.index(scheme[color])] = k
    return known


def _rotate(probs, k):
    """A reading turned k quarter turns clockwise -> the standard view (rows of the 3x3 grid)."""
    return np.rot90(probs.reshape(3, 3, 6), k).reshape(9, 6)


def _tile_costs(probs, misread_rate):
    """(9, 6) probabilities (NaN rows unseen) -> -ln P(reading | color), with the misread rate mixed in; 0 if unseen."""
    seen = ~np.isnan(probs)
    return np.where(seen, -np.log((1 - misread_rate) * np.nan_to_num(probs) + misread_rate / 6), 0.0)


def _merged_rotations(probs, costs):
    """One (9, 6) cost array per group of rotations that read the same color on every tile.

    The group's cost is the cheaper one per tile. That is optimistic (never above the exact cost of
    any member), so a search with it misses no cube; found cubes are scored exactly afterwards.
    """
    groups = {}
    for k, cost in costs.items():
        rotated = _rotate(probs, k)
        key = tuple(np.where(np.isnan(rotated[:, 0]), -1, np.nan_to_num(rotated).argmax(axis=1)))
        groups.setdefault(key, []).append(cost)
    return [np.minimum.reduce(group) for group in groups.values()]


def _exact(key, costs):
    """A cube's exact cost, choosing each face's rotation separately -> (cost, {label: rotation}, facelets)."""
    facelets = state_to_facelets(CubeState(*key))
    labels = np.array([FACES.index(ch) for ch in facelets]).reshape(6, 9)
    total, rotations = 0.0, {}
    for f in range(6):
        k, cost = min(((k, c[np.arange(9), labels[f]].sum()) for k, c in costs[f].items()), key=lambda kc: kc[1])
        total += cost
        rotations[FACES[f]] = k
    return float(total), rotations, facelets


def assemble(readings: dict, rotations: dict | None = None, scheme: dict | None = None,
             misread_rate: float = MISREAD_RATE, margin: float = MARGIN, max_contradicted: int = MAX_CONTRADICTED,
             max_candidates: int = MAX_CANDIDATES, max_nodes: int = MAX_NODES) -> AssemblyResult:
    """The legal cube(s) that best explain `readings` ({center color: 9 tile readings}); see module docstring.

    `rotations` ({center color: quarter turns}) fixes the rotation of faces where it is already known,
    e.g. from seeing the face next to a neighbor; the other faces' rotations are searched.
    """
    scheme = scheme or STANDARD_SCHEME
    color_of = {label: color for color, label in scheme.items()}
    faces = _parse(readings, scheme)
    known = _parse_rotations(rotations or {}, scheme)
    # costs[f][k]: (9, 6) cost of each color on each tile of face f, the reading turned back by k quarter
    # turns, for every rotation k still possible (one entry for an unseen face: its rotation does not matter).
    costs = [{k: _tile_costs(_rotate(faces[f], k), misread_rate) for k in ([known[f]] if f in known else range(4))}
             if f in faces else {0: np.zeros((9, 6))} for f in range(6)]

    combos = list(itertools.product(*(_merged_rotations(faces[f], costs[f]) if f in faces else [costs[f][0]]
                                      for f in range(6))))
    cost54 = np.stack([np.concatenate(combo) for combo in combos])  # (combo, 54, 6)
    corner = _piece_costs(cost54, _CORNER_IDX)
    edge = _piece_costs(cost54, _EDGE_IDX)
    bound = corner.min(axis=(2, 3)).sum(axis=1) + edge.min(axis=(2, 3)).sum(axis=1)
    order = np.argsort(bound, kind="stable")
    budget = [max_nodes]
    truncated = False

    # Phase 1: the cheapest legal cube over all rotation combinations.
    best, first = [math.inf], None
    try:
        for i in order:
            if bound[i] >= best[0] - _EPS:
                break
            for cost, *arrays in _Search(corner[i], edge[i], budget).cubes(lambda: best[0] - 2 * _EPS):  # better only
                best[0], first = cost, tuple(arrays)  # lowers the limit the running search sees
    except _OutOfBudget:
        truncated = True

    # Phase 2: every legal cube within `margin` of it, scored exactly.
    scored = {}
    if first is not None:
        scored[first] = _exact(first, costs)
        limit = scored[first][0] + margin  # at least (best exact cost + margin)
        try:
            for i in order:
                if bound[i] > limit + _EPS or len(scored) > max_candidates:
                    break
                for _, *arrays in _Search(corner[i], edge[i], budget).cubes(lambda: limit):
                    key = tuple(arrays)
                    if key not in scored:
                        exact = _exact(key, costs)
                        if exact[0] <= limit + _EPS:
                            scored[key] = exact
                    if len(scored) > max_candidates:
                        truncated = True
                        break
        except _OutOfBudget:
            truncated = True

    ranked = sorted(scored.items(), key=lambda kv: (kv[1][0], kv[1][2]))
    floor = ranked[0][1][0] if ranked else 0.0
    candidates = [_candidate(CubeState(*key), facelets, -cost, face_turns, faces, color_of)
                  for key, (cost, face_turns, facelets) in ranked[:max_candidates] if cost <= floor + margin + _EPS]
    raw = _raw(candidates[0].rotations if candidates else {}, faces, scheme)
    return _verdict(candidates, raw, truncated, max_contradicted, color_of)


def _canonical_probs(faces, rotations_by_label):
    probs = np.full((54, 6), np.nan)
    for f, p in faces.items():
        probs[9 * f:9 * f + 9] = _rotate(p, rotations_by_label.get(FACES[f], 0))
    return probs


def _candidate(state, facelets, log_likelihood, rotations, faces, color_of):
    probs = _canonical_probs(faces, rotations)
    corrected, contradicted, inferred = [], [], []
    for i in range(54):
        if i in CENTERS:
            continue
        if np.isnan(probs[i]).any():
            inferred.append(i)
            continue
        chosen = probs[i][FACES.index(facelets[i])]
        if chosen < probs[i].max() - _EPS:
            corrected.append(i)
            if chosen < CONTRADICTION:
                contradicted.append(i)
    return Candidate(state, facelets, float(log_likelihood),
                     {color_of[FACES[f]]: rotations[FACES[f]] for f in sorted(faces)},
                     tuple(corrected), tuple(contradicted), tuple(inferred))


def _raw(rotations_by_color, faces, scheme):
    rotations = {scheme[c]: k for c, k in rotations_by_color.items()}
    probs = _canonical_probs(faces, rotations)
    chars = [UNKNOWN if np.isnan(p).any() else FACES[int(np.argmax(p))] for p in probs]
    for f, i in enumerate(CENTERS):
        chars[i] = FACES[f]  # centers are known by naming
    return validate_facelets("".join(chars))


def _verdict(candidates, raw, truncated, max_contradicted, color_of):
    def names(idx):
        return " ".join(facelet_name(i) for i in idx)

    if not candidates:
        return AssemblyResult("ambiguous", [], raw, (), True, "search budget ran out before any cube was found")
    best = candidates[0]
    disputed = tuple(sorted({i for c in candidates[1:] for i in range(54) if c.facelets[i] != best.facelets[i]}))
    if len(best.contradicted) > max_contradicted:
        status = "invalid"
        message = (f"no real cube fits without overriding {len(best.contradicted)} confident readings "
                   f"({names(best.contradicted)}); rescan")
    elif len(candidates) > 1 or truncated:
        status = "ambiguous"
        more = "+" if truncated else ""
        message = f"{len(candidates)}{more} cubes fit about equally well; look again at {names(disputed) or 'more tiles'}"
    elif best.inferred:
        status = "incomplete"
        message = f"one cube fits, but {len(best.inferred)} tiles were deduced, not seen: {names(best.inferred)}"
    elif best.contradicted:
        status = "corrected"
        message = f"one cube fits best, but confident readings disagree with it; look again at {names(best.contradicted)}"
    else:
        status = "unique"
        message = "one cube fits"
    if status != "invalid" and best.corrected:
        fixes = ", ".join(f"{facelet_name(i)}={color_of[best.facelets[i]]}" for i in best.corrected)
        message += f"; readings overridden by the pieces: {fixes}"
    return AssemblyResult(status, candidates, raw, disputed, truncated, message)
