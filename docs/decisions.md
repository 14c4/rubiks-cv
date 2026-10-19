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
Date:
Status: open
Context: grid detection strategy depends on whether stickers have dark gaps between them.
Options: stickered with black plastic; stickerless.
Note (2026-10-18): the owner's cube is stickerless (captured frames in `recordings/guided/20261018_204618_auto`), with a logo on the white center.
Decision:

## D-004: Color scheme handling
Date:
Status: open
Context: cubes differ in color scheme. The state uses face labels; scanning maps colors to labels.
Decision:

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
Status: accepted
Context: the calibrated classifier (D-007/D-008) depends on values captured at calibration; the owner found any change in lighting or position degrades it and wants a method without constant calibration. The owner wants the whole system (detect the cube, read all colors, follow turns) with Claude writing everything and the process streamlined. A local RTX 4080 Super (16 GB) is available.
Options: keep classical vision (balanced clustering for scans, state-predicted verification for tracking, per-frame color constancy); per-sticker patch classifier network; full-frame segmentation network; end-to-end learned move recognition.
Decision: one full-frame segmentation network (background, cube body, hand, six colors), starting from torchvision LR-ASPP MobileNet-V3, trained mainly on synthetic frames (domain randomization, exact free labels) and fine-tuned on real self-labelled sessions; classical geometry and the cube engine on top; turn tracking by comparing engine predictions with observations, not a learned move model. New five-stage roadmap (`docs/roadmap.md`); the classical-first rule in CLAUDE.md and design.md is replaced. The D-008 classifier stays as the baseline.
Consequences: no color calibration, no manual grid; hands handled as their own class. Costs: building a synthetic renderer; a synthetic-to-real gap that only real held-out sessions can measure; network confidence must be checked before it is shown. PyTorch becomes a dependency. Revisit if the network does not beat the baseline on held-out real lighting, or if synthetic data cannot be made realistic enough (then: more real labelled data via the capture tool).
