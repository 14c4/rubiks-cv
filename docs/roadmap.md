# Roadmap

Re-planned 2026-10-18 (D-009, revised by D-011). The previous milestone plan (Milestones 0-15) is in git history; its principles carry over, its order does not.

Stages are dependency ordered. Status lives in `docs/progress.md`. Tick a box only when its acceptance evidence exists, and record that evidence in the progress log.

**The goal:** during a speedcubing-style inspection (about 15 s of turning the cube around in front of the camera, no layer turns), read all 54 tiles and reconstruct the exact cube state; then follow the turns of the solve. Trained vision models find faces and read tile colors frame by frame; evidence is accumulated over the whole inspection; the cube engine assembles, checks and identifies pieces. Only real recordings count as evidence of accuracy.

## Done

- **Exploration (old Milestone 0, 0.1-0.3):** live feed, guide grid, BGR/HSV/Lab numbers from the real cube.
- **Baseline color classifier (D-007, D-008):** calibrated, per-tile confidence; `cubetrack.ui.color_check`, `cubetrack.evaluation.color_eval`. Kept as the baseline that trained models must beat.
- **Stage 1, cube engine:** state, 18 turns, facelet conversion with validation and piece identification, x/y/z frame, text net (`src/cubetrack/cube/`).
- **Pretrained cube detector (D-010):** OWLv2 / YOLO-World, `cubetrack.ui.detect_check`; owner: "works very well" live. Used for cropping and sanity checks, not as the final per-frame model.

## Stage 2: Inspection scan (old Milestones 5-7, Checkpoint A)

- [x] 2.1 **Synthetic renderer:** random legal states from the engine, the owner's cube look (stickerless, standard scheme, logo on white center), random pose, distance, light color and intensity, shadows, glare, motion blur, hand occluders, varied backgrounds. Labels: visible cube corners, each visible face's outline, each tile's polygon, color and facelet index. Owner judges rendered vs. real frames side by side.
- [ ] 2.2 **Face geometry model (I1):** a keypoint model (e.g. YOLO pose via ultralytics) trained on 2.1, fine-tuned on real frames: per frame, the visible faces (1-3), their outlines, and a 3×3 tile grid for each, at any angle, with hands present. Plain geometry turns corners into tile quadrilaterals.
- [ ] 2.3 **Tile colors (I2):** per tile, color probabilities plus "not usable" (hand, glare, blur, off-face). Start with the baseline classifier on the grid from 2.2; then a small network on tile image patches trained on real tiles from 2.6 runs with lighting augmentation; adopt it only if it beats the baseline on held-out lighting.
- [ ] 2.4 **Accumulation (I3):** the center tile names the face (white center = white face, logo included); repeated sightings of a face are aligned (4 rotations) and their tile probabilities fused, weighted by quality; a contradiction between sightings is flagged (possible layer turn or misread). Each face's absolute rotation comes from the neighbor it was seen next to and is passed to assembly: without it some cubes are indistinguishable (the cube after U reads like the one after D'; D-012).
- [x] 2.5 **Assembly (I4):** six fused faces → one cube: search the 4^6 face rotations and the nine-per-color constraint, validate with the engine, identify every corner and edge; if several legal cubes fit, keep them and ask for a specific view instead of guessing.
- [ ] 2.6 **Live app (I5) and scramble test:** camera view with face outlines and per-tile color / piece type / confidence; a 2D net filling in as faces are seen; coverage ("bottom face not seen yet"). Scramble test mode: the app gives a scramble, the owner applies it to a solved cube and inspects, the app compares its result with the engine's expected state (exact match or which tiles were wrong, time to full coverage) and saves the labelled frames as real data.

**Acceptance:** scramble tests in at least 5 lighting setups (bright, desk shadow, dim, lamp, daylight) with free-hand inspection: exact state on held-out runs at a rate set before the final evaluation; every miss reported with its cause; no confident wrong state (an ambiguous or invalid result must say so). Raw readings, constraint-corrected result and engine-verified result kept distinct.

**Checkpoint A:** the cube is read from a normal inspection. A legitimate place to pause; a solution display (external solver, labelled as computed) and 3D view can be added here.

## Stage 3: Turn tracking (old Milestones 8-10)

- [ ] 3.1 Orientation from the visible faces and known tiles; whole-cube rotations update the reference frame only.
- [ ] 3.2 Motion detection: layer moving vs. whole cube moving vs. still.
- [ ] 3.3 After motion settles, score no-move and all 18 turns (and rotations) by comparing engine-predicted visible tiles with observations; commit only on a clear winner, otherwise mark uncertain or ask for a view.
- [ ] 3.4 Timestamped move history with confirmed / provisional / unresolved status; live virtual cube.
- [ ] 3.5 Sequences: slow scripted sequences first, then gradually faster; capture and processing separated so dropped frames are visible.

**Acceptance:** owner performs scripted sequences (provided by Claude) after an inspection scan; report insertions, deletions and substitutions against the script, not only final-state agreement.

## Later (after Stage 3 works)

Multiple-hypothesis tracking and recovery from mistakes (old 11-12), full-solve reliability evaluation (old 13), solve recording and analysis, algorithm practice (old 14-15), 3D view. Their acceptance rules from the old plan still apply when they are planned in detail.
