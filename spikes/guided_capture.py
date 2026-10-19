"""Guided capture: the window tells you which face to show; space captures it.

    python spikes/guided_capture.py [tag]

`tag` is a free label for the session (e.g. "auto" or "locked") so runs under different camera
settings can be compared later. Output goes to recordings/guided/<time>_<tag>/ (git-ignored):
  - one PNG per step (the raw frame, without the drawn grid)
  - capture.json with per-cell BGR / HSV / Lab for every step
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import grid_sample as gs

COUNTDOWN_S = 3  # after SPACE, wait this long (live preview) so your hand / shadow can leave the scene
FRAMES_PER_CAPTURE = 10  # average this many frames so one noisy frame doesn't decide the result

# (face label, what to do). The cube should be solved, so every cell of a face is one color.
STEPS = [
    ("white", "show the WHITE face flat, filling the grid"),
    ("yellow", "show the YELLOW face flat"),
    ("red", "show the RED face flat"),
    ("orange", "show the ORANGE face flat"),
    ("green", "show the GREEN face flat"),
    ("blue", "show the BLUE face flat"),
    ("white_tilt_toward", "WHITE face again, tilted so it reflects MORE light toward the camera"),
    ("white_tilt_away", "WHITE face again, tilted AWAY from the light"),
]


def capture_step(cap):
    """Average the per-cell means over several frames. Returns (bgr, hsv, lab, last_frame)."""
    total = np.zeros((3, 3, 3))
    frame = None
    for _ in range(FRAMES_PER_CAPTURE):
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("could not read a frame")
        total += gs.sample_cells(frame)
    bgr, hsv, lab = gs.convert_means(total / FRAMES_PER_CAPTURE)
    return bgr, hsv, lab, frame


def summarize(hsv, lab):
    """One line of numbers that says what this face looked like and how uneven it was."""
    h, s, v = (hsv[..., i].ravel().astype(int) for i in range(3))
    return (
        f"H {h.min()}-{h.max()}  S {s.min()}-{s.max()}  V {v.min()}-{v.max()}  "
        f"Lab median ({int(np.median(lab[..., 0]))}, {int(np.median(lab[..., 1]))}, {int(np.median(lab[..., 2]))})"
    )


def countdown(cap, seconds, label):
    """Keep showing the live view with a big number so you can step back before the capture."""
    end = time.time() + seconds
    while time.time() < end:
        ok, frame = cap.read()
        if not ok:
            return
        shown = gs.draw_guide(frame)
        put_text(shown, f"{label}: hold still... {end - time.time():.1f}", 25, (0, 0, 255))
        cv2.imshow("guided capture", shown)
        cv2.waitKey(1)


def put_text(img, text, y, color=(0, 255, 255)):
    # black outline first so the text stays readable on any background
    cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    out = Path("recordings") / "guided" / f"{time.strftime('%Y%m%d_%H%M%S')}_{tag}"
    out.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("error: camera not open (is another window still using it?)")
        return

    results = []
    step = 0
    while step < len(STEPS):
        label, instruction = STEPS[step]
        ok, frame = cap.read()
        if not ok:
            print("error: could not read a frame")
            break

        shown = gs.draw_guide(frame)
        put_text(shown, f"Step {step + 1}/{len(STEPS)}: {instruction}", 25)
        put_text(shown, "SPACE = capture   S = skip   Q = quit", 50, (255, 255, 255))
        cv2.imshow("guided capture", shown)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            step += 1
        elif key == ord(" "):
            countdown(cap, COUNTDOWN_S, label)
            bgr, hsv, lab, last = capture_step(cap)
            cv2.imwrite(str(out / f"{step + 1:02d}_{label}.png"), last)
            results.append({"step": step + 1, "label": label, "bgr": bgr.tolist(),
                            "hsv": hsv.tolist(), "lab": lab.tolist()})
            print(f"[{step + 1}/{len(STEPS)}] {label:18s} {summarize(hsv, lab)}")
            step += 1

    cap.release()
    cv2.destroyAllWindows()

    (out / "capture.json").write_text(json.dumps({"tag": tag, "steps": results}, indent=1))
    print(f"\nsaved {len(results)} captures to {out}")


if __name__ == "__main__":
    main()
