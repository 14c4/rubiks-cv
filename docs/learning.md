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

- 0.1 (2026-10-13): with DirectShow, `cap.get(cv2.CAP_PROP_FPS)` returns -1.0 ("unknown"). Measured rate was ~22.7 fps on DSHOW vs ~29.7 on MSMF at 640×480. Reported values are not measurements.

## Glossary

One line each. Claude adds entries when it explains something new.

- **Cubie:** one physical piece (center, edge, or corner).
- **Facelet:** one sticker position on the cube surface; there are 54.
- **Parity:** whether a permutation is an even or odd number of swaps. Corner and edge parities must match on a real cube.
- **Fixture:** saved input data (a recording, a state) with a known expected result, used to reproduce a test.
- **Frame:** one image from the camera, stored as a NumPy array of shape (height, width, 3) with values 0–255.
- **BGR:** OpenCV's channel order (blue, green, red), the reverse of the usual RGB.
- **Pixel coordinates:** NumPy indexes `frame[y, x]` (row first); OpenCV drawing functions take points as `(x, y)`. Origin is the top-left corner, y grows downward.
- **ROI (region of interest):** a rectangular slice of a frame, e.g. `frame[y1:y2, x1:x2]`, that you process on its own.
- **Capture backend:** the OS camera layer OpenCV talks through (on Windows: DirectShow `CAP_DSHOW` or Media Foundation `CAP_MSMF`); backends differ in what settings they report and honor.
