# Progress

Newest entry first. Claude reads the top entry at the start of each session.

## Current status

- **Re-planned 2026-10-18 (D-009, revised D-011):** goal is reading the whole cube during a free-hand inspection, then tracking turns. Stage 1 (cube engine) done; pretrained detector works live.
- **Current stage:** Stage 2, inspection scan. Color scheme confirmed standard (D-004).
- **Camera in use:** a phone through Iriun Webcam (virtual webcam). When the phone app is not connected, Iriun serves a placeholder or black frames, not an error.
- **Baseline vision:** calibrated color classifier (D-008), `python -m cubetrack.ui.color_check`.
- **Done in Stage 2:** 2.5 assembly (D-012), pure logic, tested on simulated readings.
- **Next concrete step:** 2.1 synthetic renderer (faces, tiles, corners at any angle, with labels), then 2.2 face geometry model.

## Commands that work

- `python -m pytest` : 332 tests (cube engine, rotations, color baseline, grid, detector, assembly)
- `python -m pytest -m foundation` : the 159 cube-engine and rotation tests only
- `python -m cubetrack.cube.net "R U R' U'"` : print the six-face net after a sequence from solved
- `python -m cubetrack.ui.detect_check --no-window --image <frame.png> [--backend yolo]` : pretrained cube detection on saved frames
- `python -m cubetrack.evaluation.color_eval` : cross-session / simulated-shadow table for the color classifier
- `python -m cubetrack.evaluation.assembly_eval [--known-rotations] [--confidence 0.97 0.999]` : assembly outcomes on simulated inspection readings (about 25 s)
- `python -m cubetrack.ui.color_check --model <model.json> --image <frame.png> --no-window` : replay saved frames through the predictor (run 2026-10-18 on `recordings/guided/20261018_204618_auto`)

## Log

### Entry template

```
### YYYY-MM-DD: <milestone and short title>
Completed substeps: 
Runnable behavior and evidence: 
Checks run and results (pass / fail / skipped counts): 
Supported conditions and known failures: 
Hardware checks still required: 
Next step: 
```

### 2026-10-18: Stage 2.5, assembly (D-012)
Completed substeps: 2.5
Runnable behavior and evidence: `cubetrack.vision.assemble.assemble(readings, rotations=None)`: per-face tile probabilities (faces named by center color, any rotation, tiles missing or misread) -> legal cube candidates with status unique / corrected / incomplete / ambiguous / invalid, contradicted, inferred and disputed tiles, and the engine's verdict on the raw readings. Tests use RubikTwoPhase fixture states and hand-derived cases: clean readings of single moves, 10 random scrambles and solved (known rotations): exact; 50 scrambles with rotations unknown: the scramble ties for best and every other candidate is a real rotation twin; one confident misread corrected and named; three leaning tiles settled by the pieces; twisted corner invalid with `corner_twist`; hidden UR+UF edges give exactly {solved, both flipped}; unseen D face of solved deduced; U vs D' ambiguous without rotations, unique with them. `assembly_eval`, 200 random scrambles per condition, readings 0.85-0.99, rotations unknown: clean 199 unique / 1 ambiguous (a rotation twin); 1 misread 148 corrected / 52 ambiguous; 3 misreads 195 invalid; 1 face unseen 29 deduced / 170 ambiguous; 0 WRONG anywhere; about 20 ms per assembly (1-8 ms with known rotations).
Checks run and results: `python -m pytest`: 332 passed
Supported conditions and known failures: simulated readings only. With rotations unknown, some cubes cannot be told apart (U vs D'); 2.4 must supply face rotations. With confident misreads (0.97-0.999), 3 of 400 two- or three-misread cases gave a wrong cube reported as "corrected", and 4 of 200 "one face unseen + one misread" cases came back as a wrong "incomplete" deduction. Only "unique" is a confirmed reading. Two unseen faces: usually too many candidates to list (truncated).
Hardware checks still required: none (pure logic); real fused readings arrive with 2.4/2.6
Next step: 2.1 synthetic renderer

### 2026-10-18: Pretrained cube detector (D-010)
Completed substeps: none ticked (3.0 added, in progress)
Runnable behavior and evidence: `cubetrack.vision.detect` (OWLv2 and YOLO-World), `cubetrack.ui.detect_check` (live, video and image replay; threshold keys; save key). On 8 saved frames: OWLv2 8/8 found, 0.40-0.88, ~80 ms; YOLO-World 5/8 at 0.05, 0.02-0.40, ~11 ms. PyTorch 2.11 + CUDA sees the RTX 4080 Super.
Checks run and results: `python -m pytest`: 198 passed; replay command run with both backends
Supported conditions and known failures: only flat single-face frames tested; live, hands and multi-face views untested
Hardware checks still required: owner live test with the phone camera
Next step: owner live test, then Stage 2.1

### 2026-10-18: Stage 1, cube engine
Completed substeps: 1.1-1.6
Runnable behavior and evidence: `src/cubetrack/cube/` (state, moves derived from 3D geometry, facelet conversion and validation with diagnostic codes, x/y/z reference frame, text net). Engine matches all 74 stored sequences from the independent RubikTwoPhase engine (18 single moves, 6 named, 50 seeded random up to 30 moves) and the hand-checked R fixture. Hand-derived U turn and rotation mappings pass.
Checks run and results: `python -m pytest`: 195 passed (159 foundation)
Supported conditions and known failures: face turns and x/y/z only; wide and slice moves rejected with a message
Hardware checks still required: none (optional: compare `cubetrack.cube.net` output with a physical cube)
Next step: Stage 2.1 synthetic frames

### 2026-10-18: Shadow-robust colors, logo center, edge flag (D-008)
Completed substeps: none ticked (progress on 5.4/5.6 quality flags, 6.3, 6.6)
Runnable behavior and evidence: features changed to (3 ln L*, 40 a*/L*, 40 b*/L*) + "too dark" gate; center prototypes; per-cell lightness spread flags boxes on edges/gaps ("edge"). `color_eval`: calibrate a -> b: 70/72 confident, 0 wrong; 20% simulated shadow 69/72 confident (old features: 4/69); b -> a: 54/54, shadow 49/54; zero wrong colors at any dimming. Replay on saved frames: logo center reads white 100%; the tilted frame's two boxes on gaps are flagged edge.
Checks run and results: `python -m pytest`: 36 passed
Supported conditions and known failures: pale skin reads as white at 65-79% (shown uncertain, not rejected); shadows simulated by dimming only (real shadows also shift color); constants tuned looking at both sessions, so there is no clean held-out set until new sessions are recorded
Hardware checks still required: owner live check after recalibration; recorded lighting sessions
Next step: owner records bright / desk_shadow / dim sessions (Part B)

### 2026-10-18: Color predictor with per-cell confidence (ahead of roadmap, owner request)
Completed substeps: none ticked (5.1, 6.1, 6.3 partially covered; see D-007)
Runnable behavior and evidence: `src/cubetrack/vision/color.py` (classifier), `vision/grid.py` (guide grid sampling), `ui/color_check.py` (live + replay app with calibration). Calibrated on session a, held-out session b: 0 wrong of 69 non-logo cells, all >= 90% confidence, including tilted white faces; reverse direction 0 of 53. Logo center, skin, table and gray come out "unknown"; a red/orange midpoint gets about 52/47. Replay command run on full saved frames: correct. One live frame classified headlessly: it was the Iriun placeholder (phone not connected) and all cells came out "unknown".
Checks run and results: `python -m pytest`: 22 passed
Supported conditions and known failures: fixed grid, cube held flat in it; calibration needed per lighting; not yet tested live with the cube; no temporal smoothing
Hardware checks still required: live calibration + prediction run with the phone connected
Next step: owner live run

### 2026-10-18: Milestone 0.2 and 0.3, grid sampling and color spaces
Completed substeps: 0.2, 0.3
Runnable behavior and evidence: `spikes/grid_sample.py` run live by the owner on two cube faces (4 presses each, cube still); output pasted into the session. Values were stable between presses (BGR within about 2, hue within 3). Red and orange separate clearly in V and Lab L. Observations are in `docs/learning.md`.
Checks run and results: headless check of sampling and conversion on synthetic frames with known colors: pass (spike, no pytest)
Supported conditions and known failures: orange R channel clipped at 255; white has a warm cast (Lab b about 140); red hue sits at 0-3, on the wrap-around
Hardware checks still required: exposure / white balance / focus lock (0.4); camera model not yet recorded
Next step: 0.4 (solved-face data collected afterwards is in `docs/learning.md`; `spikes/guided_capture.py` makes repeatable before/after captures)

### 2026-10-13: Milestone 0.1, live webcam feed
Completed substeps: 0.1
Runnable behavior and evidence: owner wrote `spikes/webcam.py` (DirectShow, camera 0) and reports seeing live video that closes on `q`. Claude ran a separate headless probe of camera 0 (no window): both backends open at 640×480. DSHOW reports FPS as -1.0 (unknown) and measured ~22.7 fps over 3 s; MSMF reports 29.97 and measured ~29.7 fps.
Checks run and results: none (spike, exempt from tests)
Supported conditions and known failures: DSHOW does not report frame rate; measure it instead of trusting `CAP_PROP_FPS`.
Hardware checks still required: camera model not yet recorded; which settings each backend honors (0.4)
Next step: Milestone 0.2

### 2026-10-12: Project planning
Completed substeps: none (planning only)
Runnable behavior and evidence: none
Checks run and results: none
Supported conditions and known failures: n/a
Hardware checks still required: confirm which camera settings can be locked on your machine (0.4)
Next step: Milestone 0.1
