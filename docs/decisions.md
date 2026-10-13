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
Status: proposed
Context: Moves, facelet conversion, and validation all depend on a fixed facelet order and orientation definition. Golden fixtures need an independent reference.
Options: invent a custom layout; adopt the Kociemba layout used by common solvers.
Decision: adopt Kociemba (see `docs/conventions.md`), pending verification against the `kociemba` package and a physical cube in Milestone 1.1.
Consequences: an external solver can generate and check fixtures. The rotation and color-scheme rules are still ours to define (D-002, D-004).

## D-002: Whole-cube rotations change a reference frame, not the cubie state
Date: 2026-10-12
Status: proposed
Context: `x`, `y`, `z` and physical cube rotations must not be applied twice (once to pose, once to state).
Decision: see "Open: rotations and reference frame" in `docs/conventions.md`.
Consequences: notation parsing needs the current frame. Pose tracking updates the frame only.

## D-003: Supported cube type
Date:
Status: open
Context: grid detection strategy depends on whether stickers have dark gaps between them.
Options: stickered with black plastic; stickerless.
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
