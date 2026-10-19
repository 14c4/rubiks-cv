# Rubik's Cube Tracker

A local app that watches a real 3×3 Rubik's Cube through a webcam, reconstructs its state, and follows physical turns.

Status: early exploration. See `docs/progress.md`.

## Commands

```
pip install -r requirements.txt -e .
python -m pytest
python -m pytest -m foundation
python -m cubetrack.cube.net "R U R' U'"
python -m cubetrack.ui.detect_check --no-window --image <frame.png>
python -m cubetrack.evaluation.color_eval
python -m cubetrack.ui.color_check --model <model.json> --image <frame.png> --no-window
```
