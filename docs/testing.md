# Testing and evaluation

## Mathematical correctness

The mathematical foundation must be verifiable without a camera or a 3D interface. Supply explicit starting states and move sequences, compare exact results, and run automated checks. Provide a small terminal six-face display or equivalent diagnostic view for optional physical comparison.

Explicitly encoded move tables and invariant formulas are appropriate: the engine implements fixed mathematical rules, not learned predictions. Do not hardcode scramble-specific answers or implement tests by asking the engine to generate its own expected results.

Implement the following checks as the corresponding Milestone 1–2 functionality appears. Parameterize applicable checks across `U`, `R`, `F`, `D`, `L`, and `B`, and run them from solved and reproducibly scrambled states.

### Move identities and structural checks

| Automated check | Expected result |
| --- | --- |
| A move followed by its inverse, for all eighteen face moves | Exactly the starting state |
| Four repetitions of any clockwise quarter turn | Exactly the starting state |
| Two repetitions of any half turn | Exactly the starting state |
| Two quarter turns compared with the corresponding half turn | Identical states |
| Three clockwise quarter turns compared with the inverse quarter turn | Identical states |
| `(R U R' U')` repeated six times | Exactly the starting state |
| `R U` compared with `U R`, starting from solved | Different states |
| Each quarter or inverse face turn, starting from solved | Exactly four corner slots and four edge slots change occupants; all other slots remain unchanged |
| Any face turn or legal sequence | Every edge and corner identity remains present exactly once; centers remain fixed in the cube's intrinsic frame |
| Every intermediate state in a legal sequence | Corner twist sum, edge flip sum, and permutation parity constraints remain satisfied |

Compare full permutations and orientations, not only an `is_solved` flag or a rendered face. Test enough mixed sequences to exercise moves that do not commute.

These identity checks establish internal consistency, not independent correctness. Incorrect move and inverse definitions can cancel each other. They must be paired with independent fixtures.

### Independent expected-state fixtures

Add golden fixtures with an explicit starting state, move sequence, and independently verified expected facelets or cubie arrays. Begin with each of the six clockwise face turns from solved. Add inverse turns, half turns, and mixed sequences such as `R U F' L2 D B'`.

Obtain expected outputs from documented hand-derived geometry, carefully recorded physical-cube states, or a vetted independently implemented reference engine. Record fixture provenance and normalize face order, viewing direction, color scheme, and orientation conventions before comparison. If a reference engine is used to generate fixtures, store the expected outputs so routine tests need not depend on a network service.

Never derive a golden expected state through the same production move tables, conversion helpers, or notation parser being tested. Passing random round trips is not a substitute for these fixtures.

For optional physical verification: start from solved, hold the declared orientation, execute the fixture sequence, and compare all six physical faces with the terminal display. Record verified observations once and reuse them as automated fixtures. Do not silently designate unreviewed expectations as physically verified.

### Validity and solvability fixtures

Construct invalid configurations directly through fixture data or test-only builders. Normal move functions should never create them. Unless the case specifically tests bad counts or missing pieces, preserve valid counts, piece identities, and unrelated invariants so the intended failure is isolated.

| Constructed input | Expected result |
| --- | --- |
| Solved state | Valid |
| States generated through legal face turns | Valid |
| One corner twisted in place | Invalid corner-twist sum |
| One edge flipped in place | Invalid edge-flip sum |
| Only two edges exchanged, orientations unchanged | Invalid permutation parity |
| Only two corners exchanged, orientations unchanged | Invalid permutation parity |
| Two edges and two corners exchanged, orientations unchanged | Valid: permutation parities match |
| Two corners given twists of `+1` and `+2`, all other data unchanged | Valid: total twist is zero modulo three |
| Two edges flipped, all other data unchanged | Valid: total flip is zero modulo two |
| Duplicate edge with another edge missing | Invalid piece inventory |
| Duplicate corner with another corner missing | Invalid piece inventory |
| One facelet changed to another color | Invalid color count |
| An edge containing opposite center colors | Invalid piece identity |
| A corner's sticker ordering mirrored rather than cyclically twisted | Invalid ordered corner arrangement |
| Partial scan with unknown facelets | Incomplete; do not diagnose an unsolvable physical cube |
| Wrong array sizes, out-of-range values, or malformed serialization | Rejected with useful input diagnostics |

Verify diagnostic codes, not merely that some exception occurred. Facelet fixtures may violate multiple checks; return applicable diagnostics or document validation precedence. Use direct cubie fixtures for isolated orientation/parity checks, and facelet fixtures for piece recognition and color-count checks.

### Conversion, rotation, and storage checks

- Cubie state → facelets → cubie state returns exactly the original for solved and scrambled fixtures.
- Independently specified facelet fixtures convert to the expected cubie arrays. Round trips alone can hide a shared convention error.
- Serialization → deserialization preserves all state and required scheme/reference metadata.
- Copying a state and modifying the copy leaves the original unchanged.
- Sequence inversion reverses move order and inverts each move; applying the sequence and its inverse restores the original.
- For each rigid rotation `x`, `y`, and `z`, rotation/inverse and four-quarter-rotation checks restore the original arrangement and reference frame according to the documented API contract.
- Rigid pose changes preserve the intrinsic cubie arrangement. If the API explicitly relabels a notation frame, verify the documented remapping using independent expected fixtures.
- Mixed rotations and face turns agree with independently specified reference-frame examples. This catches double-applied rotations and turns assigned to the wrong face.
- Unsupported move tokens and malformed sequences are rejected; supported whitespace and notation parse consistently.

### Reproducible randomized checks

Use a fixed documented seed and initially about 1,000 legal sequences of varied lengths. For each sequence, validate every intermediate state, verify sequence/inverse restoration, and exercise conversion and storage round trips. Print the seed, starting state, and failing sequence when a check fails.

Randomized property tests supplement independent fixtures; they do not prove the move definitions correct by themselves. Exhaustive testing is appropriate for small domains such as individual move variants. The full cube state space is far too large to exhaust.

### Running the automated foundation suite

Keep these tests independent of cameras, graphics contexts, network access, and model downloads. For the default Python stack, use pytest and configure a foundation marker or equivalent test directory so one command runs the complete implemented mathematical suite. Once configured, a suitable command is `python -m pytest -m foundation`; adapt to an existing test runner rather than adding a second one.

Run the affected foundation tests after changes to moves, conventions, conversion, serialization, or validation. Run the full foundation suite before declaring Milestones 1–2 complete. Add it to an existing CI workflow when practical; introduce a minimal workflow only when repository hosting and dependency setup are established. Do not add cameras or vision dependencies to this job merely because later milestones need them.

Report passing, failing, and skipped checks accurately. A placeholder, permanently skipped fixture, or missing independent expectation is not completion evidence. Once relevant checks pass, stop rerunning them unless code changes or new evidence justify it.


## Vision fixtures

Store fixture metadata: camera/settings, lighting, cube scheme, initial state, frame timestamps, annotations, and known limitations. Keep large recordings out of normal source commits unless explicitly intended. Provide a documented local fixture location and small redistributable fixtures where appropriate.

Include representative failures: blur, glare, similar colors, occlusion, partial faces, rigid rotations, unseen faces, rapid turns, and interruptions. Avoid building a huge fixture framework before a small useful replay exists.

## Independent ground truth

Use manually reviewed video, carefully verified staged sequences, or synchronized smart-cube telemetry when available. Validate telemetry conventions and timing rather than assuming they match the camera. Mathematical legality and final-state agreement are checks, not complete move labels.

## Metrics

Track at least:

- Scan exact-state success and rescan frequency.
- Sticker classification error and usable-observation coverage.
- Move insertions, deletions, substitutions, and exact-sequence success.
- State agreement at independently checked checkpoints.
- Fraction of session time synchronized, uncertain, or lost.
- Contradiction detection, false alarms, recovery success, and recovery duration.
- Processing latency and effective capture/processing rate.

Report abstentions and exclusions. A system that accepts only easy moves must not look perfect because uncertain moves were removed from the denominator. Separate state recovery from restoration of an exact historical move log.

Split evaluation data by session and, when possible, user/camera. Adjacent frames from one recording do not form a meaningful independent test set. Select thresholds on development data; evaluate final performance on held-out sessions.
