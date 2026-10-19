"""Sticker color predictor with a confidence on every cell.

    python -m cubetrack.ui.color_check                      # live camera
    python -m cubetrack.ui.color_check --image frame.png    # replay saved frames through the same pipeline

Hold one face of the cube inside the drawn grid. Each cell shows the predicted color and its
confidence. Cells below the confidence threshold, or not trusted as any color, get a red frame,
the reason (none = matches no color, dark = too dark to judge, edge = box not on one sticker) and
the runner-up.

The first live run starts with calibration: it asks for each face of a SOLVED cube in turn and learns
what each color looks like with your camera. Centers are learned separately, so a logo center still
reads as its face color.

Keys: SPACE = capture (calibration) / print the predictions, S = save frame + predictions for replay,
+ / - = resize grid, I J K L = move grid, C = recalibrate, Q = quit.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from cubetrack.vision.color import COLORS, ColorEstimate, ColorModel
from cubetrack.vision.grid import GuideGrid, bgr_means_to_lab8, uneven_cells

DEFAULT_MODEL = Path("calibration") / "color_model.json"
SAVE_DIR = Path("recordings") / "color_check"
CONFIDENT = 0.90  # below this a cell is drawn as uncertain
CALIBRATION_FRAMES = 10  # frames averaged per calibration capture
COUNTDOWN_S = 3.0  # time to move your hand (and its shadow) away after pressing SPACE
CENTERS = np.arange(9) == 4  # row-major index of the center cell
MOVE_STEP = 5  # pixels per I/J/K/L press
RESIZE_STEP = 2  # cell pixels per +/- press

DISPLAY_BGR = {"white": (255, 255, 255), "yellow": (0, 255, 255), "red": (0, 0, 255),
               "orange": (0, 140, 255), "green": (0, 200, 0), "blue": (255, 80, 0)}
SHORT = {"white": "W", "yellow": "Y", "red": "R", "orange": "O", "green": "G", "blue": "B", "unknown": "?"}
REASON = {"no_match": "none", "too_dark": "dark", "uneven": "edge"}
BACKENDS = {"dshow": cv2.CAP_DSHOW, "msmf": cv2.CAP_MSMF, "any": cv2.CAP_ANY}
GRID_KEYS = {ord("i"): (0, -MOVE_STEP, 0), ord("k"): (0, MOVE_STEP, 0), ord("j"): (-MOVE_STEP, 0, 0),
             ord("l"): (MOVE_STEP, 0, 0), ord("+"): (0, 0, RESIZE_STEP), ord("="): (0, 0, RESIZE_STEP),
             ord("-"): (0, 0, -RESIZE_STEP)}


def predict(grid: GuideGrid, model: ColorModel, frame: np.ndarray) -> list[ColorEstimate]:
    """The whole pipeline for one frame: sample the nine cells, convert to Lab, classify (row-major)."""
    means, spread = grid.sample(frame)
    lab = bgr_means_to_lab8(means).reshape(-1, 3)
    return model.classify(lab, centers=CENTERS, uneven=uneven_cells(spread))


def is_confident(est: ColorEstimate) -> bool:
    return est.label is not None and est.confidence >= CONFIDENT


def put_text(img, text, org, scale=0.5, color=(255, 255, 255)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def draw_grid(img, grid: GuideGrid, color=(0, 255, 0)):
    cv2.rectangle(img, (grid.x, grid.y), (grid.x + 3 * grid.cell, grid.y + 3 * grid.cell), color, 1)
    for _, _, x1, y1, x2, y2 in grid.boxes():
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)


def draw_predictions(img, grid: GuideGrid, estimates: list[ColorEstimate]):
    cv2.rectangle(img, (grid.x, grid.y), (grid.x + 3 * grid.cell, grid.y + 3 * grid.cell), (0, 255, 0), 1)
    for (_, _, x1, y1, x2, y2), est in zip(grid.boxes(), estimates):
        if is_confident(est):
            cv2.rectangle(img, (x1, y1), (x2, y2), DISPLAY_BGR[est.label], 3)
            put_text(img, f"{SHORT[est.label]} {est.confidence:.0%}", (x1 + 2, y1 + 16))
        else:
            cv2.rectangle(img, (x1 - 3, y1 - 3), (x2 + 3, y2 + 3), (0, 0, 255), 2)
            name = f"?{REASON[est.reason]}" if est.reason else f"{SHORT[est.label]} {est.confidence:.0%}"
            other, p = est.runner_up()
            put_text(img, name, (x1 + 2, y1 + 16), color=(0, 0, 255))
            put_text(img, f"/{SHORT[other]} {p:.0%}", (x1 + 2, y1 + 32), 0.4, (0, 0, 255))


def format_predictions(estimates: list[ColorEstimate]) -> str:
    lines = ["cell   label    conf   runner-up      dist(sigma)"]
    for i, est in enumerate(estimates):
        other, p = est.runner_up()
        flag = "" if is_confident(est) else f"  <- uncertain{f' ({est.reason})' if est.reason else ''}"
        lines.append(f"({i // 3},{i % 3})  {est.label or '?':7s} {est.confidence:6.1%}   "
                     f"{other:7s} {p:6.1%}   {est.distance_sigmas:5.2f}{flag}")
    return "\n".join(lines)


def load_calibration(path: Path) -> tuple[ColorModel | None, GuideGrid | None]:
    """The saved model and the grid it was calibrated with; (None, None) if absent or outdated."""
    if not path.exists():
        return None, None
    data = json.loads(path.read_text())
    try:
        model = ColorModel.from_dict(data)
    except (ValueError, KeyError) as err:
        print(f"{path}: {err}")
        return None, None
    return model, GuideGrid(*data["grid"]) if "grid" in data else None


def save_calibration(path: Path, model: ColorModel, grid: GuideGrid) -> None:
    model.save(path, extra={"grid": [grid.x, grid.y, grid.cell, grid.margin]})


def save_snapshot(frame, grid: GuideGrid, estimates) -> Path:
    """Raw frame (no overlay) + what was predicted, so a failure can be replayed later."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    stem = SAVE_DIR / time.strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(str(stem.with_suffix(".png")), frame)
    stem.with_suffix(".json").write_text(json.dumps({
        "grid": [grid.x, grid.y, grid.cell, grid.margin],
        "predictions": None if estimates is None else [
            {"label": e.label, "confidence": e.confidence, "reason": e.reason, "probabilities": e.probabilities}
            for e in estimates]}, indent=1))
    return stem.with_suffix(".png")


def run_replay(paths: list[str], model: ColorModel, fraction: float, show: bool) -> None:
    for path in paths:
        frame = cv2.imread(path)
        if frame is None:
            print(f"error: cannot read {path}")
            continue
        grid = GuideGrid.centered(frame.shape[1], frame.shape[0], fraction)
        sidecar = Path(path).with_suffix(".json")  # frames saved with S remember their grid
        if sidecar.exists() and "grid" in (meta := json.loads(sidecar.read_text())):
            grid = GuideGrid(*meta["grid"])
        estimates = predict(grid, model, frame)
        print(f"\n{path}\n{format_predictions(estimates)}")
        if show:
            shown = frame.copy()
            draw_predictions(shown, grid, estimates)
            put_text(shown, "REPLAY  any key = next", (10, 20))
            cv2.imshow("color check", shown)
            cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_live(args, model: ColorModel | None, grid: GuideGrid | None) -> None:
    cap = cv2.VideoCapture(args.camera, BACKENDS[args.backend])
    if not cap.isOpened():
        print("error: camera not open (is another program or window using it?)")
        return
    ok, frame = cap.read()
    if not ok or frame is None or frame.max() == 0:
        print("error: camera opened but delivers no picture (phone app asleep? another window using it?)")
        cap.release()
        return
    height, width = frame.shape[:2]
    if grid is None or not grid.fits(width, height):
        grid = GuideGrid.centered(width, height, args.grid_fraction)

    # calibration state
    calibrating = model is None
    cal_step, cal_samples, cal_centers = 0, {}, {}
    capture_at, captured = None, []
    estimates, message = None, ""

    while True:
        ok, frame = cap.read()
        if not ok:
            print("error: could not read a frame")
            break
        shown = frame.copy()
        now = time.monotonic()

        if calibrating:
            color = COLORS[cal_step]
            draw_grid(shown, grid)
            if capture_at is None:
                put_text(shown, f"CALIBRATE {cal_step + 1}/6: SOLVED cube, {color.upper()} face in the grid, SPACE",
                         (10, 20), color=(0, 255, 255))
            elif now < capture_at:
                put_text(shown, f"{color.upper()}: hold still... {capture_at - now:.1f}", (10, 20), color=(0, 0, 255))
            else:
                captured.append(grid.sample(frame))
                put_text(shown, f"{color.upper()}: capturing", (10, 20), color=(0, 0, 255))
                if len(captured) == CALIBRATION_FRAMES:
                    means = np.mean([m for m, _ in captured], axis=0)
                    spread = np.mean([s for _, s in captured], axis=0)
                    capture_at, captured = None, []
                    bad = np.flatnonzero(uneven_cells(spread))
                    if len(bad):  # a box on an edge or gap would teach the wrong color
                        message = f"cells {', '.join(f'({i // 3},{i % 3})' for i in bad)} not on one sticker: realign, SPACE"
                        print(message)
                    else:
                        message = ""
                        lab = bgr_means_to_lab8(means).reshape(-1, 3)
                        cal_samples[color], cal_centers[color] = lab[~CENTERS], lab[CENTERS]
                        print(f"calibrated {color}: Lab median {np.median(cal_samples[color], axis=0).astype(int)}")
                        cal_step += 1
                        if cal_step == len(COLORS):
                            model = ColorModel.fit(cal_samples, cal_centers)
                            save_calibration(args.model, model, grid)
                            print(f"saved calibration to {args.model} (sigma {model.sigma:.2f})")
                            calibrating = False
            if message:
                put_text(shown, message, (10, 45), 0.45, (0, 0, 255))
        else:
            estimates = predict(grid, model, frame)
            draw_predictions(shown, grid, estimates)
            put_text(shown, "LIVE  SPACE print  S save  +/- IJKL grid  C recalibrate  Q quit", (10, 20), 0.45)
            if message:
                put_text(shown, message, (10, 45), 0.45)

        cv2.imshow("color check", shown)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("c"):
            calibrating, cal_step, cal_samples, cal_centers = True, 0, {}, {}
            capture_at, captured, message = None, [], ""
        elif key == ord("s"):
            message = f"saved {save_snapshot(frame, grid, None if calibrating else estimates)}"
            print(message)
        elif key in GRID_KEYS and capture_at is None:
            moved = grid.moved(*GRID_KEYS[key])
            if moved.fits(width, height):
                grid = moved
                if model is not None and not calibrating:
                    save_calibration(args.model, model, grid)  # remember the placement for next time
        elif key == ord(" "):
            if calibrating and capture_at is None:
                capture_at = now + COUNTDOWN_S
            elif not calibrating and estimates is not None:
                print(format_predictions(estimates))

    cap.release()
    cv2.destroyAllWindows()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--image", nargs="+", help="replay saved frame(s) instead of using the camera")
    parser.add_argument("--no-window", action="store_true", help="replay: print only, open no window")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help=f"calibration file (default {DEFAULT_MODEL})")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--backend", choices=BACKENDS, default="dshow")
    parser.add_argument("--grid-fraction", type=float, default=0.5,
                        help="grid side as a fraction of the shorter frame side (1.0 for frames cropped to the grid)")
    args = parser.parse_args(argv)

    model, grid = load_calibration(args.model)
    if args.image:
        if model is None:
            sys.exit(f"no usable calibration at {args.model}; run live once to calibrate, or pass --model")
        run_replay(args.image, model, args.grid_fraction, show=not args.no_window)
    else:
        run_live(args, model, grid)


if __name__ == "__main__":
    main()
