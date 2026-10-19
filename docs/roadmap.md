# Roadmap

Re-planned 2026-10-18 (D-009). The previous milestone plan (Milestones 0-15) is in git history; its principles carry over, its order does not.

Stages are dependency ordered. Status lives in `docs/progress.md`. Tick a box only when its acceptance evidence exists, and record that evidence in the progress log.

**The idea:** one neural network labels every pixel of a camera frame (background, cube body, hand, six sticker colors). Classical geometry turns that into faces, 3×3 grids and per-sticker color probabilities. The cube engine holds the authoritative state. Turn tracking compares what the camera sees with what each candidate move predicts. The network is trained mostly on synthetic frames with free, exact labels; only real held-out recordings count as evidence.

## Done before the re-plan

- Milestone 0 spike (0.1-0.3): live feed, guide grid, BGR/HSV/Lab numbers from the real cube. 0.4 (camera locking) and 0.5 dropped.
- Calibrated color classifier with per-cell confidence (D-007, D-008), live app `cubetrack.ui.color_check`, evaluation `cubetrack.evaluation.color_eval`. Kept as the **baseline** the network must beat.

## Stage 1: Cube engine (old Milestones 1-2, trimmed)

Pure Python/NumPy, no camera. Conventions in `docs/conventions.md` (Kociemba layout).

- [x] 1.1 Cubie state: corner/edge permutation and orientation; identity, equality, copy, versioned serialization.
- [x] 1.2 All 18 face turns (quarter, inverse, half) and move-sequence parsing with useful errors; sequence inversion.
- [x] 1.3 Facelet conversion both ways (54-character Kociemba string), with diagnostics for impossible stickers.
- [x] 1.4 Validity checks: color counts, piece identity, duplicates/missing pieces, twist sum, flip sum, permutation parity; structured diagnostic codes; "incomplete" distinct from "invalid".
- [x] 1.5 Whole-cube rotations `x y z` through a reference frame that never edits the cubie state (resolves D-002).
- [x] 1.6 Text six-face net for inspection.

**Acceptance:** independent fixtures pass: the `R`-from-solved fixture in `docs/conventions.md`, hand-derived single turns, and an external reference engine (RubikTwoPhase's own move tables: 74 stored sequences, `tests/fixtures/cube/`). The solver round-trip check moves to Stage 4.4. Identity checks from `docs/testing.md` pass (move/inverse, four quarter turns, sexy move ×6, noncommuting pairs). Every invalid-state fixture fails for its intended reason.

## Stage 2: Data

- [ ] 2.1 Synthetic frame generator: random legal states from the engine (also mid-turn layers, for Stage 5), random pose and camera, the owner's cube look (stickerless, logo on the white center), random light color and intensity, shadows, glare, blur, noise, hand-like occluders, real backgrounds. Outputs image + per-pixel labels + face corners + sticker colors.
- [ ] 2.2 One capture tool (replaces the spikes): records frames with metadata (camera, lighting tag, time); modes: background photos (no cube), labelled session (solved cube, face by face: self-labelling), free recording for replay.
- [ ] 2.3 Real labelled data: sessions in at least 5 lighting setups (bright, desk shadow, dim, lamp, daylight), plus background photos. Annotate a small set of full frames (face corners) for detection checks.

**Acceptance:** owner judges synthetic and real frames side by side as similar; real sessions recorded with provenance; real data split by session into fine-tune and held-out sets before any training.

## Stage 3: Vision model (replaces old Milestones 5-6)

- [ ] 3.1 Segmentation network (start: torchvision LR-ASPP MobileNet-V3, pretrained), trained on synthetic frames, fine-tuned on the real fine-tune sessions. Training reproducible from one command; runs on the local GPU.
- [ ] 3.2 Geometry: from the pixel map find visible faces, fit each face's quadrilateral, place the 3×3 grid, average pixel probabilities per sticker; flag hands, glare and partial faces.
- [ ] 3.3 Confidence check: measure whether stated confidence matches accuracy on held-out real data (calibration of probabilities); fix it (e.g. temperature scaling) before the UI shows percentages.
- [ ] 3.4 Live app: automatic face detection and sticker colors with confidence, no grid alignment, no color calibration. Same pipeline for replay.

**Acceptance (held-out real sessions only):** ≥ 99% of visible stickers correct across lighting setups not used for training; confident-wrong rate below the D-008 baseline on the same data; hands labelled as hand; faces found on annotated frames with grid error small enough that every sticker box lies on its sticker.

## Stage 4: Full scan (old Milestone 7, Checkpoint A)

- [ ] 4.1 Six-face scan in any order; centers identify faces; orientation guidance so faces are not rotated or duplicated.
- [ ] 4.2 Joint assignment of all 54 stickers (exactly nine per color) using the network's probabilities.
- [ ] 4.3 Facelets → cubie state through Stage 1; validation; bounded search among uncertain stickers; targeted rescan request when still ambiguous.
- [ ] 4.4 Display the scanned cube (net); optional solution from the external solver, labelled as computed.

**Acceptance:** multiple scrambled cubes in several lighting setups scanned correctly, each verified face by face against the physical cube by the owner. Raw scan, constraint-corrected result and owner-verified result are kept distinct.

**Checkpoint A:** a validated cube scanner. A legitimate place to pause.

## Stage 5: Turn tracking (old Milestones 8-10)

- [ ] 5.1 Orientation from visible faces and known stickers; whole-cube rotations update the reference frame only.
- [ ] 5.2 Motion detection: layer moving vs. whole cube moving vs. still.
- [ ] 5.3 After motion settles, score no-move and all 18 turns (and rotations) by comparing engine-predicted visible stickers with observations; commit only on a clear winner, otherwise mark uncertain or ask for a view.
- [ ] 5.4 Timestamped move history with confirmed / provisional / unresolved status; live display.
- [ ] 5.5 Sequences: slow scripted sequences first, then gradually faster; capture and processing separated so dropped frames are visible.

**Acceptance:** owner performs scripted sequences (provided by Claude) on camera; report insertions, deletions and substitutions against the script, not only final-state agreement. A smart cube for ground truth is optional later.

## Later (after Stage 5 works)

Multiple-hypothesis tracking and recovery from mistakes (old 11-12), full-solve reliability evaluation (old 13), solve recording and analysis, algorithm practice (old 14-15), 3D view. Their acceptance rules from the old plan still apply when they are planned in detail.
