"""Record camera clips: real inspection footage and empty backgrounds (roadmap 2.1 side-by-side, later 2.6).

    python -m cubetrack.ui.record                          # live view; R starts / stops a clip, Q quits
    python -m cubetrack.ui.record --name background        # file names start with "background"
    python -m cubetrack.ui.record --seconds 10 --no-window # record 10 s at once, no window

Recording starts only on R (or --seconds) and the view shows a red REC mark while it runs. Each clip is
<out>/<name>_<time>.mp4 plus a .json with every frame's capture time (monotonic clock), so the real
frame rate is known even when the camera does not report it. Recordings stay local (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2

from cubetrack.ui.detect_check import CAMERA_BACKENDS, put_text

OUT_DIR = Path("recordings") / "clips"


class Clip:
    def __init__(self, out_dir: Path, name: str, size: tuple[int, int], fps_hint: float):
        out_dir.mkdir(parents=True, exist_ok=True)
        self.path = out_dir / f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
        self.writer = cv2.VideoWriter(str(self.path), cv2.VideoWriter_fourcc(*"mp4v"), fps_hint, size)
        self.times: list[float] = []
        self.size = size

    def add(self, frame, t: float) -> None:
        self.writer.write(frame)
        self.times.append(t)

    def close(self, source: str) -> str:
        self.writer.release()
        span = self.times[-1] - self.times[0] if len(self.times) > 1 else 0.0
        fps = (len(self.times) - 1) / span if span > 0 else 0.0
        meta = {"video": self.path.name, "source": source, "width": self.size[0], "height": self.size[1],
                "frames": len(self.times), "measured_fps": round(fps, 2),
                "times": [round(t - self.times[0], 4) for t in self.times]}
        self.path.with_suffix(".json").write_text(json.dumps(meta))
        return f"saved {self.path} ({len(self.times)} frames, {span:.1f} s, {fps:.1f} fps measured)"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--backend", choices=sorted(CAMERA_BACKENDS), default="dshow")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--name", default="inspection")
    parser.add_argument("--seconds", type=float, help="record this long immediately, then stop")
    parser.add_argument("--no-window", action="store_true")
    args = parser.parse_args(argv)
    if args.no_window and not args.seconds:
        raise SystemExit("--no-window needs --seconds")

    cap = cv2.VideoCapture(args.camera, CAMERA_BACKENDS[args.backend])
    if not cap.isOpened():
        raise SystemExit(f"camera {args.camera} did not open ({args.backend})")
    ok, frame = cap.read()
    if not ok:
        raise SystemExit("camera opened but returned no frame")
    size = (frame.shape[1], frame.shape[0])
    source = f"camera {args.camera} ({args.backend})"
    clip = Clip(args.out, args.name, size, 30.0) if args.seconds else None
    stop_at = time.monotonic() + args.seconds if args.seconds else None
    print("R = start/stop recording, Q = quit" if not args.no_window else f"recording {args.seconds} s")
    try:
        while True:
            ok, frame = cap.read()
            now = time.monotonic()
            if not ok:
                print("camera stopped delivering frames")
                break
            if clip:
                clip.add(frame, now)
            if stop_at and now >= stop_at:
                break
            if args.no_window:
                continue
            view = frame.copy()
            if clip:
                cv2.circle(view, (20, 20), 8, (0, 0, 255), -1)
                put_text(view, f"REC {now - clip.times[0]:.1f} s", (35, 26), color=(0, 0, 255))
            else:
                put_text(view, "R = record, Q = quit", (10, 26))
            cv2.imshow("record", view)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                if clip:
                    print(clip.close(source))
                    clip = None
                else:
                    clip = Clip(args.out, args.name, size, 30.0)
    finally:
        if clip:
            print(clip.close(source))
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
