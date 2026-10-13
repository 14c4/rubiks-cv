# Learning notes

This project is for exploration. This file decides who writes what, keeps questions you want answered, and collects the concepts you have learned.

## Ownership

Claude reads this table before writing code (see "Learning mode" in `CLAUDE.md`). Change it whenever you like.

| Component | Owner | Notes |
| --- | --- | --- |
| `spikes/` (Milestone 0) | You | The point is to get your hands on OpenCV |
| `cube/` moves and state (M1) | Pair | Claude proposes the data structures; you write the move tables |
| `cube/` validation (M2) | Pair | Good exercise in group theory basics |
| Tests and fixtures | Claude | You review what the tests check |
| `vision/` capture and replay (M4) | Claude | Plumbing; read it once it works |
| `vision/` geometry and color (M5–M6) | You | The core computer vision learning |
| Scan assembly (M7) | Pair | |
| Visualization (M3, M7c) | Claude | |
| `tracking/` (M8+) | Decide later | |

Owner values: **You** (Claude explains and reviews, does not write it), **Claude** (Claude writes, then explains), **Pair** (Claude sets up structure, you write the core logic).

## Questions to explore

Add questions as they come up. Move answered ones to the glossary or delete them.

- [ ] Why is Lab often better than HSV for comparing colors?
- [ ] What does a homography do, and why does it let you "flatten" a tilted cube face?
- [ ] What is camera intrinsic calibration, and when does this project actually need it?

## Spike observations

Notes from Milestone 0 and other experiments: what you tried, what you saw, what surprised you.

-

## Glossary

One line each. Claude adds entries when it explains something new.

- **Cubie:** one physical piece (center, edge, or corner).
- **Facelet:** one sticker position on the cube surface; there are 54.
- **Parity:** whether a permutation is an even or odd number of swaps. Corner and edge parities must match on a real cube.
- **Fixture:** saved input data (a recording, a state) with a known expected result, used to reproduce a test.
