"""Milestone 0.4: which camera settings does this camera + backend actually honor?

For each backend: print what the camera reports, try to switch auto-exposure / auto-white-balance /
autofocus off, and check three things separately:
  1. did set() return True?            (the driver accepted the call)
  2. does get() read back the value?   (the driver stored it)
  3. does the picture change?          (the camera actually obeyed)  <- only this one matters
"""
import sys

import cv2
import numpy as np

BACKENDS = {"DSHOW": cv2.CAP_DSHOW, "MSMF": cv2.CAP_MSMF}

PROPS = {
    "AUTO_EXPOSURE": cv2.CAP_PROP_AUTO_EXPOSURE,
    "EXPOSURE": cv2.CAP_PROP_EXPOSURE,
    "AUTO_WB": cv2.CAP_PROP_AUTO_WB,
    "WB_TEMPERATURE": cv2.CAP_PROP_WB_TEMPERATURE,
    "AUTOFOCUS": cv2.CAP_PROP_AUTOFOCUS,
    "FOCUS": cv2.CAP_PROP_FOCUS,
    "BRIGHTNESS": cv2.CAP_PROP_BRIGHTNESS,
    "CONTRAST": cv2.CAP_PROP_CONTRAST,
    "SATURATION": cv2.CAP_PROP_SATURATION,
    "GAIN": cv2.CAP_PROP_GAIN,
}


def grab(cap, n=8):
    """Read n frames (the driver needs a few to apply a change) and return the last one."""
    frame = None
    for _ in range(n):
        ok, frame = cap.read()
        if not ok:
            return None
    return frame


def mean_bgr(frame):
    return frame.reshape(-1, 3).mean(axis=0).round(1)


def try_set(cap, name, value):
    before = cap.get(PROPS[name])
    accepted = cap.set(PROPS[name], value)
    after = cap.get(PROPS[name])
    print(f"  {name:15s} set({value:>6}) accepted={accepted!s:5}  read back {before} -> {after}")
    return after


def probe(backend_name, backend):
    print(f"\n===== {backend_name} =====")
    cap = cv2.VideoCapture(0, backend)
    if not cap.isOpened():
        print("  could not open camera 0")
        return
    grab(cap, 15)

    print("reported by the camera:")
    for name, prop in PROPS.items():
        print(f"  {name:15s} {cap.get(prop)}")

    base = grab(cap)
    print("baseline mean BGR (auto everything):", mean_bgr(base))

    print("\nswitching autos off (values differ per backend, so try the usual ones):")
    for value in (0.25, 0, 1):  # DSHOW uses 0.25 = manual; MSMF/V4L style uses 0 or 1
        try_set(cap, "AUTO_EXPOSURE", value)
    try_set(cap, "AUTO_WB", 0)
    try_set(cap, "AUTOFOCUS", 0)

    print("\nexposure sweep (does brightness really change?). Exposure is log2 seconds on DSHOW:")
    for e in (-2, -4, -6, -8, -10):
        cap.set(cv2.CAP_PROP_EXPOSURE, e)
        frame = grab(cap)
        print(f"  EXPOSURE {e:>3}: read back {cap.get(cv2.CAP_PROP_EXPOSURE):>6}  mean BGR {mean_bgr(frame)}")

    print("\nwhite balance sweep (does the color cast change?):")
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    for t in (3000, 4500, 6500):
        cap.set(cv2.CAP_PROP_WB_TEMPERATURE, t)
        frame = grab(cap)
        print(f"  WB_TEMPERATURE {t}: read back {cap.get(cv2.CAP_PROP_WB_TEMPERATURE):>6}  mean BGR {mean_bgr(frame)}")

    cap.release()


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(BACKENDS)
    for name in wanted:
        probe(name, BACKENDS[name])
