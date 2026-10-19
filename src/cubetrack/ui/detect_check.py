"""Try pretrained cube detection on the live camera or on saved frames / videos.

    python -m cubetrack.ui.detect_check                         # live, OWLv2 (accurate, ~12 fps)
    python -m cubetrack.ui.detect_check --backend yolo          # live, YOLO-World (fast, weaker)
    python -m cubetrack.ui.detect_check --image a.png b.png     # replay frames (prints results)
    python -m cubetrack.ui.detect_check --video clip.mp4        # replay a recording

The best box is drawn thick with its score; other boxes above the threshold thin. Scores are the
model's own (OWLv2 and YOLO-World use different scales), not calibrated probabilities.

Keys: + / - = raise / lower threshold, S = save frame + detections (recordings/detect_check/),
SPACE = pause, Q = quit.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2

from cubetrack.vision.detect import BACKENDS, DEFAULT_PROMPT, DEFAULT_THRESHOLD, Detection, best, make_detector

SAVE_DIR = Path("recordings") / "detect_check"
CAMERA_BACKENDS = {"dshow": cv2.CAP_DSHOW, "msmf": cv2.CAP_MSMF, "any": cv2.CAP_ANY}


def put_text(img, text, org, scale=0.55, color=(255, 255, 255)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def draw(img, detections: list[Detection], status: str):
    top = best(detections)
    for d in detections:
        thick = 3 if d is top else 1
        cv2.rectangle(img, d.box[:2], d.box[2:], (0, 255, 0) if d is top else (0, 200, 255), thick)
    if top:
        put_text(img, f"cube {top.score:.2f}", (top.box[0], max(15, top.box[1] - 6)), color=(0, 255, 0))
    else:
        put_text(img, "no cube above threshold", (10, 45), color=(0, 0, 255))
    put_text(img, status, (10, 20), 0.5)


def describe(detections: list[Detection]) -> str:
    if not detections:
        return "  no detections above threshold"
    return "\n".join(f"  score {d.score:.2f}  box {d.box}" for d in sorted(detections, key=lambda d: -d.score))


def save(frame, detections, backend, threshold) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    stem = SAVE_DIR / time.strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(str(stem.with_suffix(".png")), frame)
    stem.with_suffix(".json").write_text(json.dumps({"backend": backend, "threshold": threshold, "detections": [
        {"box": d.box, "score": d.score, "label": d.label} for d in detections]}, indent=1))
    return stem.with_suffix(".png")


def run_images(detector, paths, threshold, show):
    for path in paths:
        frame = cv2.imread(path)
        if frame is None:
            print(f"error: cannot read {path}")
            continue
        t0 = time.perf_counter()
        dets = detector.detect(frame, threshold)
        ms = (time.perf_counter() - t0) * 1000
        print(f"{path}  ({ms:.0f} ms)\n{describe(dets)}")
        if show:
            shown = frame.copy()
            draw(shown, dets, f"REPLAY {detector.name}  thr {threshold:.2f}  any key = next")
            cv2.imshow("detect check", shown)
            cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_stream(detector, cap, threshold, source_label):
    paused, frame, dets, ms = False, None, [], 0.0
    while True:
        if not paused or frame is None:
            ok, frame = cap.read()
            if not ok:
                print("end of stream" if source_label == "REPLAY" else "error: could not read a frame")
                break
            t0 = time.perf_counter()
            dets = detector.detect(frame, threshold)
            ms = (time.perf_counter() - t0) * 1000
        shown = frame.copy()
        draw(shown, dets, f"{source_label} {detector.name}  thr {threshold:.2f}  {ms:.0f} ms/frame"
                          f"{'  PAUSED' if paused else ''}   +/- thr  S save  SPACE pause  Q quit")
        cv2.imshow("detect check", shown)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key in (ord("+"), ord("=")):
            threshold = min(0.95, threshold + 0.05)
        elif key == ord("-"):
            threshold = max(0.01, threshold - 0.05)
        elif key == ord(" "):
            paused = not paused
        elif key == ord("s"):
            print(f"saved {save(frame, dets, detector.name, threshold)}\n{describe(dets)}")
    cap.release()
    cv2.destroyAllWindows()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--backend", choices=BACKENDS, default="owl")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--threshold", type=float, help="default: 0.20 for owl, 0.05 for yolo")
    parser.add_argument("--image", nargs="+", help="replay saved frames")
    parser.add_argument("--video", help="replay a recorded video")
    parser.add_argument("--no-window", action="store_true", help="--image only: print results, open no window")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--camera-backend", choices=CAMERA_BACKENDS, default="dshow")
    args = parser.parse_args(argv)
    threshold = args.threshold if args.threshold is not None else DEFAULT_THRESHOLD[args.backend]

    print(f"loading {args.backend} detector (first run downloads weights into models/) ...")
    detector = make_detector(args.backend, args.prompt)
    if args.image:
        run_images(detector, args.image, threshold, show=not args.no_window)
        return
    cap = cv2.VideoCapture(args.video) if args.video else cv2.VideoCapture(args.camera, CAMERA_BACKENDS[args.camera_backend])
    if not cap.isOpened():
        print("error: could not open " + (args.video or f"camera {args.camera}"))
        return
    run_stream(detector, cap, threshold, "REPLAY" if args.video else "LIVE")


if __name__ == "__main__":
    main()
