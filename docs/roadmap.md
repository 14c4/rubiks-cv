# Milestone roadmap

Milestones are dependency ordered. A temporary diagnostic UI or uncertainty indicator may be added earlier when it helps validate the current milestone. Coaching remains deferred until the tracking foundation is demonstrated.

Status lives in `docs/progress.md`. Tick boxes here only when a substep's acceptance evidence exists, and record that evidence in the progress log.

Items marked **(added)** were not in the first draft of this plan.

## Phase 0 — Exploration

### Milestone 0: OpenCV spike (throwaway) **(added)**

Purpose: learn what is actually hard before building rigor around it. Code lives in `spikes/` and is exempt from the testing and documentation rules.

- [x] 0.1 Open the webcam with OpenCV and show the live feed in a window.
- [ ] 0.2 Draw a fixed 3×3 guide grid and sample the mean color of each cell.
- [ ] 0.3 Print the samples in BGR, HSV, and Lab while holding up each face.
- [ ] 0.4 Try to lock exposure, white balance, and focus; record which settings your camera and OS actually honor.
- [ ] 0.5 Note what goes wrong (glare, red/orange confusion, auto-exposure drift) in `docs/learning.md`.

**Acceptance:** You have seen real numbers from your cube under your lighting, and you know which camera settings you can and cannot control. Nothing here needs tests.

## Phase 1 — Mathematical foundation

### Milestone 1: Core cube-state engine

- [ ] 1.1 Specify face, axis, piece, orientation, and notation conventions.
- [ ] 1.2 Define six centers, twelve edge identities, and eight corner identities.
- [ ] 1.3 Represent piece identity separately from position and orientation.
- [ ] 1.4 Implement all eighteen face turns: quarter, inverse, and half turns.
- [ ] 1.5 Parse move sequences, reject unsupported notation, and generate inverses.
- [ ] 1.6 Implement whole-cube rotations with an explicit reference-frame contract.
- [ ] 1.7 Implement equality, copy semantics, serialization, and facelet conversion.

**Acceptance:** Known independently specified states match move outputs. Four quarter turns and move/inverse pairs restore the original state. Random sequences and their inverses round-trip. Serialization and facelet/cubie conversions round-trip. Include noncommuting move examples; inverse tests alone can miss consistently incorrect move definitions.

### Milestone 2: Physical validity and solvability

- [ ] 2.1 Validate complete facelet counts, center assignment, and supported scheme.
- [ ] 2.2 Reject nonexistent edge/corner combinations and invalid ordered corner arrangements.
- [ ] 2.3 Detect duplicate or missing edges and corners.
- [ ] 2.4 Check corner twist sum equals zero modulo three.
- [ ] 2.5 Check edge flip sum equals zero modulo two.
- [ ] 2.6 Check corner and edge permutation parities agree.
- [ ] 2.7 Return structured, specific diagnostics and distinguish incomplete input.

**Acceptance:** Legal generated states pass. A single twisted corner, single flipped edge, edge-only pair swap, duplicate piece, incorrect color count, and mirrored corner fail for the intended reasons. A valid matching edge/corner parity change passes. Never describe a low-quality invalid scan as proof that the physical cube is unsolvable.

### Milestone 3: Virtual cube visualization

- [ ] 3.1 Render all stickers from the authoritative state in an inspectable 3D view. **Deferred until after Checkpoint A.**
- [ ] 3.2 Provide a flat six-face net or equivalent view for exact inspection.
- [ ] 3.3 Animate face turns and rigid rotations consistently with state updates. **Deferred until after Checkpoint A.**
- [ ] 3.4 Support manual controls, scramble, reset, undo, and replay.
- [ ] 3.5 Show move history and relevant reference orientation.
- [ ] 3.6 Label manual/synthetic mode clearly.

Before Checkpoint A, a terminal or 2D six-face net is enough. Build the 3D view once a scanner exists to feed it.

**Acceptance:** Rendered stickers match the engine after known and randomized sequences. Undo/replay restore exact states. Animation queues preserve move order. Do not claim camera tracking at this checkpoint.

## Phase 2 — Camera observation and scanning

### Milestone 4: Camera infrastructure

- [ ] 4.1 Implement camera selection and configurable capture settings.
- [ ] 4.1a Disable or lock auto exposure, auto white balance, and autofocus where the backend allows; read back and log the values actually applied. Document per-OS limits in `docs/capture-setup.md`. **(added)**
- [ ] 4.2 Show actual resolution, measured frame rate, frame age, and processing time.
- [ ] 4.3 Handle unavailable devices, disconnections, and clean shutdown.
- [ ] 4.4 Add explicit local recording and deterministic replay controls.
- [ ] 4.5 Establish a repeatable setup and document lighting, distance, and angle in `docs/capture-setup.md`, including flicker from LED or fluorescent lighting.
- [ ] 4.6 Support camera intrinsic calibration when pose estimation requires it; distinguish this from color calibration.
- [ ] 4.7 Add timestamped debug overlays without blocking capture indefinitely.

**Acceptance:** A recorded fixture runs through the same observation pipeline as live frames. Capture reports measured settings rather than assuming requested settings were honored. Backpressure and dropped frames remain observable.

### Milestone 5: Cube and sticker geometry

- [ ] 5.0 Declare the supported cube type (stickered with black plastic, or stickerless). Grid detection that relies on dark gaps between stickers does not work on stickerless cubes. **(added)**
- [ ] 5.1 Begin with a guided region of interest if needed; label any manual assistance.
- [ ] 5.2 Detect visible face quadrilaterals and score geometric quality.
- [ ] 5.3 Rectify faces or project a consistent 3×3 grid onto them.
- [ ] 5.4 Locate sticker sampling regions away from borders and glare.
- [ ] 5.5 Track usable regions across frames.
- [ ] 5.6 Identify partial faces, occlusion, motion blur, and loss of detection.
- [ ] 5.6a Treat hands and fingers as the dominant occluder. Skin tones sit near orange, red, and yellow; do not classify skin as a sticker. **(added)**
- [ ] 5.7 Overlay geometry and failure reasons on live and replay footage.

**Acceptance:** Grids align with manually checked visible faces on controlled recordings. Record detection coverage and geometric errors. A fixed guide box is an assisted scan mechanism, not evidence of automatic face detection.

### Milestone 6: Color and cubie recognition

- [ ] 6.1 Calibrate color prototypes from the actual cube under current lighting. The six centers are free per-session prototypes.
- [ ] 6.2 Compare suitable color representations, initially HSV or Lab, on fixtures.
- [ ] 6.3 Preserve multiple color candidates and quality scores for ambiguous samples.
- [ ] 6.3a For a complete scan, assign all 54 stickers jointly under the constraint that each color appears exactly nine times (balanced clustering or assignment), and compare its accuracy against independent per-sticker classification. **(added)**
- [ ] 6.4 Associate stickers into cubie observations only when geometry supports it.
- [ ] 6.5 Filter impossible piece combinations using the established inventory.
- [ ] 6.6 Reject or downweight glare, shadows, blur, and occluded samples.
- [ ] 6.7 Aggregate stable observations without blending different turns or poses.

**Acceptance:** Evaluate sticker classifications against independent annotations. Inspect red/orange and white/glare failures explicitly. Distance-based scores must not be presented as calibrated probabilities unless calibration has been measured. A sticker seen alone does not uniquely identify its cubie.

### Milestone 7: Complete scan and reconstruction

- [ ] 7.1 Guide a six-face scan with explicit face order and orientation instructions.
- [ ] 7.2 Use centers and orientation references to avoid rotated or duplicated face captures.
- [ ] 7.3 Require no layer turns during the scan; invalidate/rescan if the state changes.
- [ ] 7.4 Assemble facelets and convert them into cubie candidates.
- [ ] 7.5 Validate inventory, ordered orientations, and global solvability.
- [ ] 7.6 Search bounded alternatives among uncertain observations when justified.
- [ ] 7.7 Preserve competing legal candidates and request targeted rescans when needed.
- [ ] 7.8 Display the reconstructed cube for six-face physical comparison.

**Acceptance:** Independently verify every face on multiple legal scrambled cubes. Record scan failures and corrections. Distinguish raw scan, constraint-corrected candidate, and physically verified result. Do not select an arbitrary legal candidate merely because it is solvable.

**Checkpoint A:** A useful, validated cube scanner exists. This is a deliverable even before live turn tracking works. It is also a legitimate place to stop.

### Milestone 7b: Solution display **(added)**

- [ ] 7b.1 Convert a physically verified scan to the reference solver's input format.
- [ ] 7b.2 Show a solution sequence and step through it on the virtual cube.
- [ ] 7b.3 Label the solution as computed from the scan, not observed.

**Acceptance:** Applying the displayed solution to the scanned state in the cube engine yields the solved state. A solver is an external dependency; it must not replace the project's own validity checks.

### Milestone 7c: 3D view (deferred items 3.1 and 3.3) **(added)**

Build the 3D rendering and animation from Milestone 3 now that real scans exist to display.


## Phase 3 — Physical movement tracking

### Milestone 8: Pose and whole-cube orientation

- [ ] 8.1 Establish cube-to-camera geometry and camera calibration requirements.
- [ ] 8.2 Estimate pose from visible geometry and supported correspondences.
- [ ] 8.3 Track rigid motion without changing the internal cubie arrangement.
- [ ] 8.4 Use known sticker/cubie observations to distinguish plausible orientations.
- [ ] 8.5 Account for symmetric-looking faces and ambiguous poses.
- [ ] 8.6 Handle occlusion, loss, and reacquisition with visible status.
- [ ] 8.7 Keep display pose and notation frame consistent.

**Acceptance:** Record rigid rotations with no layer turns, starting from both solved and scrambled states. The internal state remains unchanged, and orientation uncertainty appears when the evidence is insufficient.

### Milestone 9: Isolated face turns

- [ ] 9.0 Set up independent move labels before building detection. A Bluetooth smart cube gives timestamped moves; synchronize its clock to the camera with a deliberate visible event. **(added)**
- [ ] 9.1 Identify stable observation windows before and after a movement.
- [ ] 9.2 Detect evidence of layer motion versus rigid cube motion.
- [ ] 9.3 Generate plausible no-turn, face-turn, and pose-change candidates.
- [ ] 9.4 Apply candidate turns through the cube engine.
- [ ] 9.5 Project/compare expected visible stickers with observations.
- [ ] 9.6 Rank candidates using appearance, geometry, and temporal evidence.
- [ ] 9.7 Commit only with sufficient evidence; otherwise retain ambiguity.
- [ ] 9.8 Emit timestamped move events and update the virtual state.

**Acceptance:** Test slow isolated quarter, inverse, and half turns across all faces, with sufficient visibility or an explicit request for another view. Include no-move and rigid-rotation controls. Two quarter turns and one half-turn can have identical endpoints; preserve observed event detail rather than inventing timing.

### Milestone 10: Continuous move tracking

- [ ] 10.1 Track short sequences without resetting after each move.
- [ ] 10.2 Maintain move intervals, state snapshots, and orientation history.
- [ ] 10.3 Handle whole-cube rotations between layer turns.
- [ ] 10.4 Preserve uncertainty through brief occlusions and dropped frames.
- [ ] 10.5 Detect gaps that may contain multiple moves.
- [ ] 10.6 Increase supported speed gradually using measured recordings.
- [ ] 10.6a Separate capture from processing (threads or processes) so slow frames are dropped visibly rather than stalling capture. Measure before optimizing. **(added)**
- [ ] 10.7 Display tracking, uncertain, lost, and rescan-needed states.

**Acceptance:** Compare predefined sequences against independent move labels and resulting states. Report insertions, deletions, and substitutions, not only final-state agreement. Declare supported notation explicitly; slice and wide turns must be supported deliberately or identified as outside the current scope.

## Phase 4 — Reliability and recovery

### Milestone 11: Multiple-hypothesis state estimation

- [ ] 11.1 Define observation and transition scoring transparently.
- [ ] 11.2 Preserve a bounded set of candidate states and poses.
- [ ] 11.3 Reject candidates contradicted by reliable visible evidence.
- [ ] 11.4 Use later frames to revise earlier provisional moves.
- [ ] 11.5 Bound search depth, beam width, and processing budget.
- [ ] 11.6 Handle equivalent states without erasing distinct possible histories.
- [ ] 11.7 Expose confirmed, provisional, and unresolved history.

**Acceptance:** Occluded-turn fixtures resolve when later evidence distinguishes alternatives. Irrecoverably ambiguous examples remain unresolved. Measure candidate counts, pruning behavior, and runtime; pruning must not masquerade as certainty.

### Milestone 12: Error detection and resynchronization

- [ ] 12.1 Detect persistent prediction/observation contradictions.
- [ ] 12.2 Separate bad observations, uncertain pose, and likely move-history errors.
- [ ] 12.3 Revisit recent low-quality intervals within a bounded history window.
- [ ] 12.4 Search alternative legal move sequences and compare them to video evidence.
- [ ] 12.5 Apply supported corrections with an auditable revision record.
- [ ] 12.6 Request a precise clearer view or targeted rescan when needed.
- [ ] 12.7 Support full state reacquisition without destroying the session record.
- [ ] 12.8 Mark unrecoverable history gaps even when state synchronization returns.

**Acceptance:** Inject missed, extra, and incorrect moves into labeled replay sessions. Measure detection rate, false alarms, automatic recovery, requested recovery, and recovery time. Solving a discrepancy must not erase evidence of the original error.

### Milestone 13: Full solves and reliability evaluation

- [ ] 13.1 Scan and independently verify the initial state.
- [ ] 13.2 Track controlled full solves and retain evidence throughout.
- [ ] 13.3 Verify the physical ending state through adequate independent views.
- [ ] 13.4 Check the inferred sequence against initial and ending states.
- [ ] 13.5 Report unresolved intervals and avoid false success declarations.
- [ ] 13.6 Evaluate separate recordings with varied users and capture conditions.
- [ ] 13.7 Report move-history quality, state correctness, coverage, recovery, and latency.
- [ ] 13.8 Establish a measured operating envelope and optimize actual bottlenecks.

**Acceptance:** Set numeric acceptance thresholds before final evaluation and meet them on held-out recordings. Publish sample counts, conditions, exclusions, and results. A visible solved face or a predicted solved state alone is insufficient proof that the entire physical cube is solved.

**Checkpoint B:** The core tracker is demonstrated under a documented operating envelope. Controlled slow solves and unrestricted speed solves remain separate capability claims.

## Phase 5 — Features built on reliable tracking

### Milestone 14: Solve recording and analysis

- [ ] 14.1 Save and replay solves with state, move, and correction history.
- [ ] 14.2 Display move timing, pauses, move count, and turning-rate statistics.
- [ ] 14.3 Specify counting conventions such as half-turn or quarter-turn metric.
- [ ] 14.4 Recognize known sequences with explicit handling of rotations and equivalent notation.
- [ ] 14.5 Detect supported method phases from cube-state conditions.
- [ ] 14.6 Compare sessions and display uncertainty in derived statistics.
- [ ] 14.7 Exclude unresolved history from claims requiring exact moves.

**Acceptance:** Compare analytics with independently labeled solves. Differentiate identical endpoint transformations from identical executed algorithms. Tracking errors must not become confident coaching conclusions.

### Milestone 15: Algorithm practice and dataset improvement

- [ ] 15.1 Add a verified algorithm library and setup states.
- [ ] 15.2 Guide practice and verify observed execution.
- [ ] 15.3 Identify supported mistakes and hesitation intervals.
- [ ] 15.4 Suggest targeted drills from sufficiently reliable evidence.
- [ ] 15.5 Introduce optional, explicit recording/data-sharing consent if requested.
- [ ] 15.6 Collect independently verified labels and review uncertain sessions.
- [ ] 15.7 Evaluate any learned model against the existing baseline and held-out data.

**Acceptance:** Practice feedback matches labeled executions. Training data provenance and label quality are recorded. A chosen algorithm is an intention, not proof of execution; tracker output is a prediction, not automatic ground truth.
