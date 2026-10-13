# Vision-Based Rubik's Cube Tracker

## Project objective

Build a local application that observes a real standard 3×3 Rubik's Cube through an ordinary camera, reconstructs its initial state, follows physical turns, and maintains an accurate virtual cube and timestamped move history.

The core product is reliable tracking. Analytics and coaching come afterward. A polished interface or an animation driven by simulated moves does not demonstrate working camera tracking.

Start with one cube, one fixed webcam, stable lighting, a clear background, and deliberately slow turns. Expand supported conditions only after measuring performance.

This is also a learning project. The owner is new to computer vision and wants to understand how each part works, not only to have it built.

## Where things live

| File | Read it when |
| --- | --- |
| `docs/roadmap.md` | Choosing what to build next; milestone substeps and acceptance criteria |
| `docs/conventions.md` | Before touching moves, orientation, facelet conversion, or rotations |
| `docs/testing.md` | Writing or running tests; fixture and evaluation rules |
| `docs/design.md` | Data contracts, component boundaries, interface rules, known limits, recording rules |
| `docs/capture-setup.md` | Camera, lighting, and supported operating conditions |
| `docs/decisions.md` | Before making or revisiting a consequential design choice |
| `docs/learning.md` | Who writes which component; open questions; glossary |
| `docs/progress.md` | Start of every session: current status and next step |

## How to work in this repository

1. Read `docs/progress.md` and inspect the repository (git status, configuration, current code) before changing anything.
2. Follow the current request. The roadmap is direction, not authorization to implement every milestone in one session.
3. For a new repository with no narrower request, start at Milestone 0 in `docs/roadmap.md`. Do not scaffold future components.
4. When continuing, find the earliest incomplete dependency, state the immediate target in one line, and implement a concrete, runnable increment.
5. Preserve working code and unrelated changes. Extend the current stack rather than rewriting it. Add dependencies only for a present problem.
6. Run checks appropriate to the change. Fix failures the change caused, then move on. Do not rerun unchanged checks or loop on review and refactoring.
7. Finish with what works, how it was verified, material limitations, and the exact command to try it.
8. Update `docs/progress.md` when a milestone advances. Mark a substep done only when its acceptance evidence exists.
9. Record consequential choices in `docs/decisions.md`.

Proceed autonomously on routine implementation choices. Ask only when missing information blocks the work or a consequential choice cannot be inferred. If a camera is unavailable, finish the code and replay support and name the hardware check still required. Never claim a live-camera test happened when it did not.

Do not start multi-agent workflows unless the owner asks.

### README

Only add or update commands in the README's "Commands" section, and only commands you have actually run successfully. Change the rest of the README only when asked.

## Learning mode

`docs/learning.md` assigns each component an owner. Respect it:

- **Owner writes:** do not implement it. Explain the concept, point to the relevant OpenCV or NumPy functions, give hints or small illustrative snippets outside the source tree, and review code the owner wrote. Write it yourself only if the owner explicitly asks for that specific piece.
- **Claude writes:** implement normally, then explain the non-obvious parts in a few sentences.
- **Pair:** propose the structure and interfaces; the owner fills in the core logic; you write tests and glue.

When the owner asks how something works, answer with reference to this repository's actual code and data where possible, and do not edit files unless asked. Prefer explanations the owner can verify by running something (print a value, show an intermediate image).

When explaining a new concept, add a one-line entry to the glossary in `docs/learning.md` if it is not already there.

Code in `spikes/` is throwaway exploration: no tests, no documentation requirements, never imported by `src/`.

## Non-negotiable principles

Details and rationale are in `docs/design.md` and `docs/testing.md`.

- **Pieces are immutable.** Six centers, twelve edges, eight corners, each with a permanent identity. Moves change position and orientation, never colors. The authoritative state is cubie-based; facelets are a derived view that must convert consistently both ways. Never invent pieces to satisfy an observation.
- **Observations are evidence.** Keep observation, hypothesis, and accepted estimate as separate objects. An accepted estimate can be wrong; keep enough history to detect contradictions and recover.
- **Legality is necessary, not sufficient.** Every legal turn preserves the invariants, so mistaking `R` for `R'` still yields a legal state. Detect wrong moves by comparing predicted visible stickers with observations. State synchronization and move-history correctness are different claims.
- **Uncertainty stays visible.** Support provisional and unresolved moves from the first camera milestone. Missing evidence never becomes a confident prediction; request a specific view or rescan instead.
- **Reproducibility first.** One pipeline for live and replayed frames. Debug vision failures from saved fixtures. Keep raw observations when applying corrections.
- **Independent test expectations.** Never derive a golden expected state with the production code being tested.

## Technical direction

- Python, NumPy, OpenCV, and pytest, in a virtual environment. Source in `src/cubetrack/`, tests in `tests/`.
- Cube mathematics (`cube/`) imports nothing from OpenCV or any UI library. The camera pipeline is independent of rendering.
- Classical vision and constrained state estimation first. Add learned models only after a recorded failure pattern and a measured baseline.
- Never use an LLM to transform cube states, decide solvability, or track frames.
- Local only. No cloud services, accounts, databases, or paid APIs unless asked.
- Large recordings stay out of git (see `.gitignore`); small redistributable fixtures may be committed.

## Definition of done for a session

The requested increment is implemented, runnable, and verified to the extent available. `docs/progress.md` reflects reality. Remaining hardware checks and limitations are stated precisely. Nothing outside the request is required to call it done.

Priority order: **correct cube mathematics → trustworthy observations → verified scanning → live tracking → measured recovery and reliability → training features.**
