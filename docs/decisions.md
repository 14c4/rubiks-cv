# Decision log

One entry per consequential choice: a convention, a library, an algorithm, a scope boundary. Short is fine. The point is that six weeks from now you (or Claude) can see why something is the way it is instead of re-arguing it.

Status values: `proposed`, `accepted`, `superseded by D-NNN`.

## Template

```
## D-NNN: <title>
Date: YYYY-MM-DD
Status: proposed | accepted | superseded by D-NNN
Context: what problem forced a choice
Options: what was considered
Decision: what was chosen
Consequences: what this makes easier or harder; what would make us revisit it
```

---

## D-001: Cube state conventions follow the Kociemba layout
Date: 2026-10-12
Status: accepted 2026-10-18 (engine matches 74 RubikTwoPhase reference sequences)
Context: Moves, facelet conversion, and validation all depend on a fixed facelet order and orientation definition. Golden fixtures need an independent reference.
Options: invent a custom layout; adopt the Kociemba layout used by common solvers.
Decision: adopt Kociemba (see `docs/conventions.md`), pending verification against the `kociemba` package and a physical cube in Milestone 1.1.
Consequences: an external solver can generate and check fixtures. The rotation and color-scheme rules are still ours to define (D-002, D-004).

## D-002: Whole-cube rotations change a reference frame, not the cubie state
Date: 2026-10-12
Status: accepted 2026-10-18 (`cube/frame.py`; x follows R, y follows U, z follows F)
Context: `x`, `y`, `z` and physical cube rotations must not be applied twice (once to pose, once to state).
Decision: see "Open: rotations and reference frame" in `docs/conventions.md`.
Consequences: notation parsing needs the current frame. Pose tracking updates the frame only.

## D-003: Supported cube type
Date: 2026-10-18
Status: accepted
Context: grid detection strategy depends on whether stickers have dark gaps between them.
Options: stickered with black plastic; stickerless.
Note (2026-10-18): the owner's cube is stickerless (captured frames in `recordings/guided/20261018_204618_auto`), with a logo on the white center.
Decision: support the owner's stickerless cube first. Tile boundaries come from learned face geometry (D-011), not from dark gaps; stickered cubes are not a goal until measured.

## D-004: Color scheme handling
Date: 2026-10-18
Status: accepted
Context: cubes differ in color scheme. The state uses face labels; scanning maps colors to labels.
Decision: the owner's cube uses the standard scheme (U white, F green, R red, D yellow, L orange, B blue; opposites white/yellow, red/orange, green/blue). The scanner names each face by its center color, independent of how the cube is held, so no scan orientation is required. Serialized scans record the scheme.

## D-005: Visualization approach
Date:
Status: open
Context: Milestone 3 needs a 2D net now and a 3D view after Checkpoint A (Milestone 7c). Choose one simple approach and document it here.
Options: OpenCV-drawn net only; a Python 3D library; a browser frontend (e.g. three.js) fed by a local server.
Decision:

## D-006: Ground truth for move labels
Date:
Status: open
Context: Milestones 9–13 need independent move labels. Hand-labeling video is slow.
Options: hand-labeled video; staged scripted sequences; Bluetooth smart cube telemetry.
Decision:

## D-007: Sticker color classifier: calibrated Lab prototypes with an "unknown" option
Date: 2026-10-18
Status: superseded by D-008 (features and constants; structure kept)
Context: the owner asked for a working camera color predictor with a confidence per square now, ahead of Milestones 1-5, skipping the rest of Milestone 0 (0.4 exposure lock, 0.5 notes). Two real solved-cube sessions showed hue stable within a face but saturation and lightness shifting with shadow and tilt; white's hue overlaps orange and yellow; the white center carries a logo.
Options: fixed HSV thresholds; nearest prototype in HSV; nearest prototype in Lab; a learned model.
Decision: features (0.5 x L*, a*, b*) from OpenCV Lab; one prototype per color calibrated from the 8 non-center cells of each solved face under the current lighting; Gaussian scores with a shared spread (floor 4) plus an "unknown" option at 4 sigma; confidence is the normalized probability (`src/cubetrack/vision/color.py`). L weight and thresholds chosen on session 2026-10-18a, checked on held-out 2026-10-18b: 0 errors on 69 cells (incl. tilted white), and 0 on 53 cells the other way.
Consequences: needs a six-face calibration per lighting setup (no built-in default). Confidences are near 100% whenever a sample sits close to its prototype; they are honest about "between two colors" and "no color", but not yet validated against lighting changes after calibration. Revisit if a recorded session shows errors, if auto-exposure drift breaks a calibration, or when the 54-sticker joint assignment (6.3a) is built.

## D-008: Shadow-robust color features, center prototypes, edge flag
Date: 2026-10-18
Status: accepted
Context: owner's first live run: calibrating in a bright spot and moving to the desk (phone shadow) dropped confidence at once; logo center showed `?`; corners sometimes `?` in bright light. Simulated 20% dimming reproduced it: 4/69 cells confident with D-007 features, never a wrong color (distances in sigma blew up because shadow shrinks L*, a*, b* together).
Options: recalibrate per location; rg chromaticity (most shadow-proof in simulation but accepted light skin as a sticker); lightness-normalized Lab (chosen); online adaptation of prototypes (rejected: can reinforce its own errors).
Decision: features (3 ln L*, 40 a*/L*, 40 b*/L*); sigma floor 3; unknown at 3.75 sigma; samples darker than 0.35x the darkest calibrated sticker are "too dark". Each face's center is learned as a separate center-only prototype (logo reads as its face color; non-center cells never use it). A box whose lightness std exceeds 8 (aligned stickers: at most 2.4; box on a gap: about 40) is "uneven" and not trusted; centers are exempt (logos are textured). Calibration rejects captures with uneven boxes. Constants picked looking at sessions 2026-10-18a/b and simulated dimming, so they are not yet held-out results.
Consequences: one calibration now tolerates mild shadow (a->b at 0.8x: 69/72 confident; b->a: 49/54; zero wrong at any dimming). Cost: pale skin sits near white (65-79%, shown uncertain), so hands need geometry (5.6a), not color. Revisit with real recorded lighting sessions (bright / desk_shadow / dim): real shadows also change color, and auto exposure / white balance may help or hurt.

## D-009: Re-plan around a segmentation network trained on synthetic data
Date: 2026-10-18
Status: superseded by D-011 (vision architecture and stage order); the move to learned vision and real-only evidence stands
Context: the calibrated classifier (D-007/D-008) depends on values captured at calibration; the owner found any change in lighting or position degrades it and wants a method without constant calibration. The owner wants the whole system (detect the cube, read all colors, follow turns) with Claude writing everything and the process streamlined. A local RTX 4080 Super (16 GB) is available.
Options: keep classical vision (balanced clustering for scans, state-predicted verification for tracking, per-frame color constancy); per-sticker patch classifier network; full-frame segmentation network; end-to-end learned move recognition.
Decision: one full-frame segmentation network (background, cube body, hand, six colors), starting from torchvision LR-ASPP MobileNet-V3, trained mainly on synthetic frames (domain randomization, exact free labels) and fine-tuned on real self-labelled sessions; classical geometry and the cube engine on top; turn tracking by comparing engine predictions with observations, not a learned move model. New five-stage roadmap (`docs/roadmap.md`); the classical-first rule in CLAUDE.md and design.md is replaced. The D-008 classifier stays as the baseline.
Consequences: no color calibration, no manual grid; hands handled as their own class. Costs: building a synthetic renderer; a synthetic-to-real gap that only real held-out sessions can measure; network confidence must be checked before it is shown. PyTorch becomes a dependency. Revisit if the network does not beat the baseline on held-out real lighting, or if synthetic data cannot be made realistic enough (then: more real labelled data via the capture tool).

## D-010: Pretrained text-prompted detector for locating the cube
Date: 2026-10-18
Status: proposed (owner testing live)
Context: the owner asked to try pretrained object detection instead of waiting for a trained network. No off-the-shelf model knows stickers or colors, but open-vocabulary detectors can box "a Rubik's cube" without training.
Options: YOLO-World v2 x (ultralytics); OWLv2 base ensemble (transformers); Grounding DINO (not tried).
Decision: both behind one interface (`src/cubetrack/vision/detect.py`), OWLv2 default. On the 8 saved frames (single flat faces, 640x480): OWLv2 found all 8, scores 0.40-0.88, about 80 ms/frame on the RTX 4080 Super; YOLO-World scored 0.02-0.40, missed 3 at threshold 0.05, about 11 ms/frame. Weights download once into `models/` (git-ignored); Ultralytics telemetry disabled (`yolo settings sync=False`).
Consequences: possible shortcut for Stage 3 (crop to the cube) and for labelling real data. Unknown until measured: hands, multiple faces visible, motion blur, other objects. Scores are not calibrated probabilities. Revisit after live testing and a measured detection rate on recordings.

## D-011: Inspection scan with face geometry model, per-tile colors and accumulation
Date: 2026-10-18
Status: accepted
Context: the owner's goal is to read the whole cube during a speedcubing-style inspection: the cube turned freely in the hand for about 15 s, 2-3 faces visible at a time, fingers in view, no guided face-by-face prompts. Per-pixel color segmentation (D-009) merges neighbouring same-color tiles on a stickerless cube into one blob, so it cannot give tile positions. The pretrained detector (D-010) finds the cube reliably but knows nothing about faces or tiles.
Options: per-pixel segmentation + geometry; trained tile detector; face/corner keypoint model + per-tile color model + accumulation over frames.
Decision: (1) a keypoint model trained on synthetic renders (fine-tuned on real frames) gives visible faces and their 3×3 grids at any angle; (2) per-tile color probabilities from the baseline classifier first, then a small patch network trained on real tiles if it beats the baseline; (3) evidence accumulated over the inspection, faces named by their center color; (4) the engine resolves the 4^6 face rotations, the nine-per-color constraint, validity and piece identities. Verification by a scramble test: a known scramble applied to a solved cube, inspected, compared with the engine's expected state. Roadmap rewritten: Stage 2 inspection scan, Stage 3 turn tracking.
Consequences: piece type and identity come from geometry and the engine, not from vision. Synthetic data is needed mainly for geometry (corners), which is easier to make realistic than colors; color training can rely on real tiles labelled by scramble tests. Revisit if the keypoint model fails on real hand-held frames after fine-tuning, or if accumulation cannot separate a misread from a layer turn.

## D-012: Assembly by piece-level maximum likelihood, with honest statuses
Date: 2026-10-18
Status: accepted
Context: roadmap 2.5 turns six faces of per-tile color probabilities (each face named by its center, in an unknown rotation, some tiles missing or misread) into a cube state. It must report ambiguity, incompleteness and invalidity instead of guessing. scipy (Hungarian algorithm) is not installed.
Options: take each tile's most likely color and validate (fails on any misread); balance colors to nine each (does not know about pieces); search over pieces with likelihood scores (chosen).
Decision: (1) each reading becomes a cost -ln P(reading | color) with a 2% misread rate mixed in; (2) a cube is chosen piece by piece (each corner/edge once, legal twist and flip sums, matching parity), which implies nine-per-color; (3) all 4^6 face-rotation combinations get a vectorized lower bound and only promising ones are searched; rotations of a face that read identically are merged optimistically, and every cube found is scored exactly per face; (4) branch and bound (NumPy only) finds the best cube and every cube within ln 100 of it. Status: unique (clear winner, all seen, no confident reading contradicted) / corrected (clear winner that overrides 1-2 confident readings: look again) / incomplete (deduced tiles) / ambiguous (`disputed` tiles to look at) / invalid (more than 2 confident readings contradicted). Raw readings are validated by the engine separately. Optional known face rotations (`rotations=`) restrict the search (`src/cubetrack/vision/assemble.py`).
Consequences: with rotations unknown, some cubes are indistinguishable (U vs D', found by the tests), so 2.4 should pass each face's rotation from the neighbor it was seen next to. Legal cubes can differ in only 3 tiles, so two or three confident misreads can make another cube fit best; this is why only "unique" counts as confirmed. Simulated evaluation (`cubetrack.evaluation.assembly_eval`, 200 scrambles per condition): zero WRONG unique answers in every condition; with confident misreads (0.97-0.999), 3 of 400 two- or three-misread cases were wrong but reported as "corrected", and 4 of 200 "one face unseen + one misread" cases came back as a wrong "incomplete" deduction. Revisit the margin and misread rate with real fused readings from 2.4/2.6.

## D-013: Synthetic renderer written in NumPy and OpenCV
Date: 2026-10-18
Status: accepted (owner chose option A)
Context: roadmap 2.1 needs many frames with exact labels (cube corners, face outlines, tile polygons, colors, facelet indices) to train the face geometry model (2.2). No 3D renderer is installed. The owner holds the cube facing the camera (capture-setup.md).
Options: A. own renderer in NumPy + OpenCV; B. Blender (photoreal, large install, slow, hard to follow); C. OpenGL libraries (pyrender, moderngl; extra dependencies, awkward headless on Windows).
Decision: A. Each visible face is painted flat as a texture (rounded tiles, dark grooves, logo, per-texel lighting with tilted normals at tile rims), then pasted into the image with a homography from its four projected corners. Geometry comes from the engine (`cube/moves.py` GEOMETRY), so drawn tiles cannot disagree with the conventions. Realism comes from randomization (pose, size, light, colors, backgrounds, procedural fingers, shadows, blur, noise, compression), not from physically exact lighting. Real background frames can be mixed in.
Consequences: no new dependencies; fast enough to generate thousands of frames; labels exact by construction. Weak points: fingers are simple shaded capsules, shadows are approximate, no reflections or real materials. Revisit (Blender) if the owner's side-by-side judgement or the 2.2 model's results on real frames show the gap is too large.

## D-014: Real hands in synthetic frames, cut out with OWLv2 + SAM
Date: 2026-10-19
Status: accepted
Context: the owner judged the drawn hands (D-013) "very bad": they hide what a real grip looks like. The face geometry model (2.2) must learn to find faces and tiles under real fingers.
Options: better procedural hands; a 3D hand model; real hands cut out of the owner's clips (chosen).
Decision: `cubetrack.synth.hands` extracts, once per clip, the owner's hands from inspection footage: OWLv2 boxes the cube and the hands, SAM (facebook/sam-vit-base, local, weights in models/) turns hand boxes into masks, and a skin-chroma check learned from each frame's own hand pixels removes slivers of cube or shirt (frames where that removes over 25% of SAM's mask are skipped). Each crop stores the real cube's box; the renderer scales and moves it so that box lands on the rendered cube's box (jitter: scale +-10%, rotation +-15 degrees, random mirror) and uses the pasted alpha as the occluder label. Drawn hands stay only as a fallback without a library. Hands come only from `inspection_scramble1`; `deeper_inspection` is kept out of all training data for evaluation.
Consequences: grips, skin and finger detail are real. Limits: one person, one session, one lighting; the parts of the hands the real cube hid are missing (the rendered cube covers them unless its pose differs a lot); hands do not change with the rendered light except through the global camera effects. Both clips come from the same evening, so a truly held-out test for 2.2 needs a later recording session.

## D-015: Face geometry model: YOLO pose with a 4x4 tile-corner lattice per face
Date: 2026-10-19
Status: proposed (owner to confirm the plan and acceptance thresholds in docs/roadmap.md 2.2)
Context: roadmap 2.2 needs, per frame, each visible face's tile grid at any angle with fingers over the cube; output feeds tile colors (2.3) and accumulation (2.4). Training data: synthetic frames with exact labels (2.1, D-013/D-014). Installed: ultralytics 8.4.182 (YOLO11, YOLO12, YOLO26 pose; AGPL-3.0), PyTorch with CUDA, RTX 4080 Super.
Options: A. YOLO pose: each face an object with 16 keypoints (the 4x4 lattice of tile corners) in an image-based order, a homography on top; B. a small network predicting order-free heatmaps (face regions, lattice points), then grouping points into faces with RANSAC homographies; C. corner-only keypoints (4 per face).
Decision (proposed): start with A. It trains with an existing, well-tested tool in hours; 16 points give redundancy when fingers hide corners (vs C); the homography makes the grid exact for a flat face. Its known weakness: a square face has no visible "first" corner, so the keypoint order must follow an image rule that flips near 45 degree tilts; the dev-set error analysis measures how much that costs, and B is the fallback because heatmaps have no order to get wrong. Acceptance is judged on real frames only: a dev set from `deeper_inspection` and a test set from a later session, both hand-clicked by the owner, never pre-filled by a model.
Consequences: needs a click-labelling tool and ~45 minutes of owner labelling; per-point occlusion flags in the renderer labels. AGPL-3.0 is fine for a local personal project but matters if the app is ever distributed (then: retrain with a permissively licensed implementation, e.g. approach B in plain PyTorch). Revisit after 2.2e's error analysis.
