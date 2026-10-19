# Design reference

Detail behind the principles in `CLAUDE.md`. Read the relevant section when working on that component.

## Design principles in full

### Physical pieces are immutable

A conventional 3×3 has six centers, twelve edges, and eight corners. Centers carry one color, edges two, and corners three. Each edge and corner has a permanent identity; moves change its position and orientation, never its colors.

Use a cubie-based authoritative state. A facelet representation is also useful for scanning, rendering, and interoperability, but it must convert consistently to and from the cubie model.

Never invent pieces to satisfy an observation. Maintain the known piece inventory and reject duplicate pieces, missing pieces, impossible combinations, and invalid sticker arrangements.

### Camera observations are evidence

Keep three distinct objects:

- **Observation:** what the vision pipeline measured, including uncertainty and visibility.
- **Hypothesis:** a candidate cube state, pose, and move history that could explain those observations.
- **Accepted estimate:** the interpretation currently supported sufficiently for the application to use.

An accepted estimate can still be wrong. Preserve enough observations and history to detect contradictions and recover.

### Mathematical legality is necessary, not sufficient

A complete scanned state must satisfy piece identity, orientation, and parity constraints. These can eliminate impossible scans.

However, every legal face turn preserves these invariants. Mistaking `R` for `R'` still produces a legal state. During tracking, compare predicted visible stickers and geometry with actual observations. Rechecking solvability alone cannot detect an incorrect legal move.

Different move sequences can also produce the same state. `R R'` and no move have identical endpoints. Distinguish **state synchronization** from **move-history correctness**; verifying one does not establish the other.

### Uncertainty must remain visible

Support provisional and unresolved observations or moves. Missing evidence must not become a fabricated high-confidence prediction. When automatic recovery cannot distinguish candidates, request a specific clearer view or rescan.

Uncertainty and recovery begin with the first camera milestone. Milestones 11–12 deepen these capabilities; they are not the first time the application acknowledges uncertainty.

### Reproducibility comes first

Use one processing pipeline for live capture and recorded replay. Reproduce vision failures from saved fixtures instead of repeatedly debugging only against a live webcam. Keep raw observations available when applying mathematical correction so a correction does not become its own evidence.

## Technical direction in full

For an empty repository, prefer Python, NumPy, OpenCV, and pytest for the mathematical and vision foundation. Use a minimal local interface first. Introduce a dedicated 3D frontend and communication layer when Milestone 3 requires them; choose one simple approach and document it.

These are defaults, not reasons to replace an established implementation. Keep cube mathematics independent of OpenCV and UI libraries. Keep the camera pipeline independent of rendering and future coaching.

Vision uses a segmentation network trained mostly on synthetic, automatically labelled frames, with classical geometry on top (D-009). It replaced the classical-first rule after a recorded failure (lighting changes broke calibrated colors) and a measured baseline (D-008). Real held-out sessions are the only accepted evidence of vision accuracy; synthetic results are development aids. State estimation stays constrained and explicit. Do not use an LLM to perform cube-state transformations, decide solvability, or serve as the per-frame tracking engine.

Local processing is the initial deployment model. Cloud infrastructure, accounts, databases, external APIs, and paid services are outside the core milestones unless requested.

## Component boundaries

Create modules as needed; this is a responsibility map, not a demand to create empty directories.

| Component | Responsibility |
| --- | --- |
| `cube/` | Cubie state, notation, moves, rotations, facelet conversion, validity checks |
| `vision/` | Capture/replay, geometric detection, colors, scanning, pose observations |
| `tracking/` | Move candidates, observation scoring, state estimation, history, recovery |
| `evaluation/` | Fixture metadata, independent labels, benchmark tools and results |
| `frontend/` or local UI | Camera display, virtual cube, scan guidance, controls, uncertainty |
| `docs/` | Conventions, setup, progress, supported conditions, evaluation notes |

Avoid duplicated cube logic across components or languages. Rendering consumes the authoritative state; it must not independently calculate a second cube state that can drift.

### Data contracts to establish as components appear

- **CubeState:** corner permutation/orientation, edge permutation/orientation, and scheme/reference metadata as needed.
- **Frame:** capture timestamp, frame index, source identifier, image, and actual dimensions. Use a monotonic clock for live elapsed time and recorded timestamps for replay.
- **Sticker/face observation:** image location, face geometry, candidate colors or scores, visibility, and quality flags.
- **Pose estimate:** camera-relative orientation/position, supporting correspondences, uncertainty, and reference frame.
- **Move event:** move, time interval, confirmed/provisional/unresolved status, supporting evidence, and alternatives when needed.
- **Tracking hypothesis:** candidate state, pose/reference orientation, score, recent history, and parent provenance.
- **Validation result:** valid/invalid/incomplete, diagnostic codes, implicated positions, and limitations.

Begin with simple typed structures. Add persistence or transport schemas when necessary. An incomplete scan is not automatically an invalid physical cube.

## Interface requirements

Prioritize a readable camera view, aligned observation overlays, an inspectable virtual cube, move history, and clear tracking status. Show actionable requests such as “show the back face” or “hold still for a clearer scan.”

Clearly identify live, replay, manual, and synthetic modes. A frozen last-known cube must be labeled as stale or uncertain after tracking loss. Never animate unobserved turns as if they were confirmed.

During scanning, show captured faces, orientation guidance, ambiguous stickers, and validation diagnostics. Offer targeted correction/rescan rather than silently replacing colors. Manual correction should remain labeled as manual evidence.

Use polish when it improves inspection and control. Do not prioritize landing pages, dashboards, elaborate settings, accounts, or algorithm libraries over a working tracking milestone.

## Limits that must shape implementation

- A single camera cannot observe all pieces simultaneously. Some turn histories are fundamentally indistinguishable under occlusion.
- A higher frame rate helps but does not compensate for unusable exposure, blur, or hidden stickers. Measure actual capture quality.
- Geometric or mathematical constraints narrow interpretations; they do not manufacture missing visual evidence.
- An apparently unsolvable scan may be caused by color classification, face orientation, or reconstruction errors. Require reliable rescanning before making a physical-cube claim.
- Learning models require trustworthy labels and evaluation. More automatically labeled footage can reinforce errors.
- If state is recovered through a new scan, previously hidden turns may remain unknown. Keep the move-log gap visible.

## Recording and data handling

Process locally by default. Recording starts only through an explicit action, with a visible indicator and configurable output location. Do not upload webcam footage automatically. Keep unnecessary personal background information out of shared fixtures where practical.

If crowdsourced collection is later implemented, separate participation from basic app use. Explain what is collected, obtain explicit consent, provide deletion controls, and record label provenance. These future features must not block local development of the tracker.
