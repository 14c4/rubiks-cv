# Progress

Newest entry first. Claude reads the top entry at the start of each session.

## Current status

- **Re-planned 2026-10-18 (D-009, revised D-011):** goal is reading the whole cube during a free-hand inspection, then tracking turns. Stage 1 (cube engine) done; pretrained detector works live.
- **Current stage:** Stage 2, inspection scan. Color scheme confirmed standard (D-004).
- **Camera in use:** a phone through Iriun Webcam (virtual webcam). When the phone app is not connected, Iriun serves a placeholder or black frames, not an error.
- **Baseline vision:** calibrated color classifier (D-008), `python -m cubetrack.ui.color_check`.
- **Done in Stage 2:** 2.1 synthetic renderer (D-013, D-014; owner approved the side-by-side 2026-10-19); 2.5 assembly (D-012), pure logic, tested on simulated readings.
- **Setup (owner, 2026-10-18):** camera faces the owner, who holds the cube up and turns it (capture-setup.md).
- **Real clips (local, `recordings/clips/`):** two inspection clips of a known scramble (state in `*.cube.json`; the slow one verified on four faces), one background clip. Camera not mirrored. Training uses `inspection_scramble1` (hands) and `background`; `deeper_inspection` is kept out of training for evaluation.
- **Next concrete step:** plan 2.2 face geometry model. Data habit: add short clip pairs (inspection + background) in new conditions; keep one separate session out of training as the test.

## Commands that work

- `python -m pytest` : 364 tests (cube engine, rotations, color baseline, grid, detector, assembly, renderer)
- `python -m pytest -m foundation` : the 159 cube-engine and rotation tests only
- `python -m cubetrack.cube.net "R U R' U'"` : print the six-face net after a sequence from solved
- `python -m cubetrack.ui.detect_check --no-window --image <frame.png> [--backend yolo]` : pretrained cube detection on saved frames
- `python -m cubetrack.evaluation.color_eval` : cross-session / simulated-shadow table for the color classifier
- `python -m cubetrack.evaluation.assembly_eval [--known-rotations] [--confidence 0.97 0.999]` : assembly outcomes on simulated inspection readings (about 25 s)
- `python -m cubetrack.synth.hands --clips <inspection clip> --out data/hands` : cut the owner's hands out of a clip (OWLv2 + SAM, GPU, about 2 min for 35 s of video)
- `python -m cubetrack.synth.generate --out data/synth/v1 --count 2000 --backgrounds <background clip> --hands data/hands` : synthetic frames + JSON labels, about 33 frames/s with 8 workers
- `python -m cubetrack.synth.sheet --out sheet.png [--labels] [--real <frames or video>]` : contact sheet; labels drawn; real vs synthetic side by side
- `python -m cubetrack.ui.record [--name background]` : record clips (R start/stop) with per-frame timestamps; headless run `--seconds 2 --no-window` tested with the phone disconnected only
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

### 2026-10-19: Stage 2.1, real hands (D-014)
Completed substeps: 2.1 (owner: renders "look good" next to the held-out real clip, 2026-10-19)
Runnable behavior and evidence: owner judged the drawn hands "very bad". `cubetrack.synth.hands` now cuts the owner's real hands out of `inspection_scramble1` (OWLv2 boxes, SAM masks, skin-chroma cleanup): 239 crops from 278 sampled frames (every 3rd), 61 MB in `data/hands`. Pasted so the real cube's box matches the rendered cube's, with soft shadows; the pasted alpha is the occluder label. `data/synth/v1` regenerated: 2000 frames, 108 MB, 33 frames/s. Comparison sheet uses the held-out `deeper_inspection` as the real side.
Occlusion and variety (measured): share of the cube's box covered by hands, real frames (hand library, 278 sampled, frames without usable hands counted as 0) p10/p50/p90 0.00 / 0.18 / 0.35; synthetic (300 frames, same measure) 0.00 / 0.22 / 0.38. Over the 2000 frames: 1 / 2 / 3 faces visible 5% / 34% / 60%; 73% of visible-face tiles clearly visible, 10% hidden; 91% of faces turned toward the camera keep at least 5 of 9 tiles visible; 2% of frames have fewer than 5 clearly visible tiles; cube width p10/p50/p90 108 / 173 / 290 px. Narrow: hands from 35 s of one clip, backgrounds from one 33 s clip (one room, shirt, evening).
Checks run and results: `python -m pytest`: 366 passed (2 new: paste alignment within a pixel of the hand-computed position; pasted hands lower tile visibility in the labels)
Supported conditions and known failures: one person / session / lighting; hand parts the real cube hid are missing, visible as gaps when the rendered cube's pose differs a lot; a few crops include a shadowed forearm
Hardware checks still required: none
Next step: plan 2.2

### 2026-10-18: Stage 2.1 renderer tuned to the owner's real clips
Completed substeps: none ticked (owner judgement pending)
Runnable behavior and evidence: owner recorded `inspection_scramble1` (34.7 s), `deeper_inspection` (44.1 s, pauses on faces) and `background` (32.7 s), all 640x480 at a steady 24 fps. The scramble had been applied holding blue up / white facing the owner (x'): the four faces paused on match the engine's state for that hold exactly, and no other of 24 holds x 4 rotations x mirrored or not; state saved next to each clip (`*.cube.json`; the first clip's state assumed, not cross-checked). Camera not mirrored (owner's paper test). OWLv2 on 80 inspection frames (0 missed): cube box 124 / 150 / 183 px wide (p10 / p50 / p90), center at 0.59 width, 0.66 height. Renderer now: 70% of poses around that size and place; usually two hands (fingertips over the left and right edges, thumbs below, palms behind), fingers 0.3-0.42 of the cube's width, half the hands in the owner's measured skin tone; motion blur up to 25 px in half the frames; real background frames from the clip in 80% of frames. `data/synth/v1` regenerated (1000 frames, 22 frames/s).
Checks run and results: `python -m pytest`: 364 passed
Supported conditions and known failures: fake hands are smooth, cartoonish shapes; real background frames sometimes contain the owner's own hands not holding anything (fine as distractors); one room and one lighting so far
Hardware checks still required: none for 2.1 beyond the owner's judgement
Next step: owner judges `data/synth/sheets/real_vs_synthetic.png`; then 2.2

### 2026-10-18: Stage 2.1 synthetic renderer, first version (D-013)
Completed substeps: none ticked (2.1 needs the owner's side-by-side judgement on real clips from the camera-facing setup)
Runnable behavior and evidence: `cubetrack.synth` (render: engine geometry, pinhole camera, lit face textures pasted with homographies, labels; scene: random pose / look / light, procedural room-and-person or real backgrounds, palm behind the cube, tapered fingers with shadows, exposure / white balance / blur / noise / JPEG; generate: parallel dataset writer, frame i seeded by (seed, i); sheet: contact sheets). Labels per frame: 8 cube corners (visible, occluded, in frame), each visible face's outline in reading order and its 9 tiles (quad, center, color, facelet index, visible share). 1000 frames written to `data/synth/v1` (49 MB) at about 20 frames/s. First real-vs-synthetic sheet showed wide black grooves where the owner's stickerless cube has thin seams in the tile's own color; fixed. `cubetrack.ui.record` added for the owner's clips.
Checks run and results: `python -m pytest`: 364 passed (32 new). Pixel test: colors at labelled tile centers match RubikTwoPhase fixture states from two corner views; mirroring the texture on purpose made all 20 cases fail. Face reading order matches docs/conventions.md for all six faces; corner counts 4 / 6 / 7 for 1 / 2 / 3 faces; occluder test hides exactly the covered column and corners.
Supported conditions and known failures: fingers are shaded capsules and the palm sometimes shows as a disk; procedural backgrounds look cartoonish (real background clips are supported and should dominate); no reflections, cube edges not rounded; the logo is random red strokes. Only compared with old flat desk frames so far.
Hardware checks still required: owner records an inspection clip and a background clip in the camera-facing setup (recorder only tested headless with the phone disconnected: black frames, 10.7 fps); owner judges `sheet --real`.
Next step: owner clips and judgement, then 2.2

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
