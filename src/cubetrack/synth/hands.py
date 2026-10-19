"""Real hands for synthetic frames (D-014): cut out of the owner's clips, pasted around a rendered cube.

    python -m cubetrack.synth.hands --clips recordings/clips/inspection_scramble1_*.mp4 --out data/hands

Extraction (once, GPU): in every few frames, OWLv2 (vision/detect.py) boxes the cube and the hands; SAM
("Segment Anything", facebook/sam-vit-base, downloaded once into models/) turns each hand box into a
pixel mask. The masks include fingers lying over the cube and leave the cube itself out. Each frame's
hands are saved as one BGRA crop plus the real cube's box in that crop (data/hands/index.json).

Pasting: the crop is scaled and moved so the real cube's box lands on the rendered cube's box, with a
little jitter and a random mirror (a left hand becomes a right one). The parts of the hands that the
real cube hid are missing, but the rendered cube covers the same place. The pasted alpha is the
occluder label for tile visibility.

Keep evaluation clips out of the library: a clip whose hands are pasted into training frames is no
longer a fair test.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

MARGIN = 1.2  # crop this many cube-box sizes around the cube on each side


class HandLibrary:
    """Hand crops on disk (read lazily, so worker processes stay small)."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.entries = json.loads((self.folder / "index.json").read_text())["hands"]

    def __len__(self) -> int:
        return len(self.entries)

    def load(self, entry: dict) -> np.ndarray:
        return cv2.imread(str(self.folder / entry["file"]), cv2.IMREAD_UNCHANGED)

    def paste(self, rng: np.random.Generator, canvas: np.ndarray, cube_box, jitter: bool = True,
              shadow=None) -> np.ndarray:
        """Paste a random hand crop over `canvas` (float BGR 0..1) so its cube box matches `cube_box`
        (x0, y0, x1, y1 in canvas pixels). `shadow`: image direction the hands' shadow falls (None: no
        shadow). Returns the hands' alpha (canvas size)."""
        entry = self.entries[rng.integers(len(self.entries))]
        return paste_hands(rng, canvas, self.load(entry), entry["cube_box"], cube_box, jitter, shadow)


def paste_hands(rng, canvas, crop_bgra, real_box, target_box, jitter=True, shadow=None) -> np.ndarray:
    h, w = canvas.shape[:2]
    rx0, ry0, rx1, ry1 = real_box
    tx0, ty0, tx1, ty1 = target_box
    scale = math.sqrt(((tx1 - tx0) * (ty1 - ty0)) / max((rx1 - rx0) * (ry1 - ry0), 1.0))
    angle, shift, mirror = 0.0, np.zeros(2), False
    if jitter:
        scale *= rng.uniform(0.9, 1.1)
        angle = rng.uniform(-15, 15)
        shift = rng.normal(0, 0.05, 2) * (tx1 - tx0)
        mirror = rng.random() < 0.5
    crop = crop_bgra[:, ::-1] if mirror else crop_bgra
    real_center = np.array([(rx0 + rx1) / 2, (ry0 + ry1) / 2])
    if mirror:
        real_center[0] = crop.shape[1] - 1 - real_center[0]
    target_center = np.array([(tx0 + tx1) / 2, (ty0 + ty1) / 2]) + shift
    m = cv2.getRotationMatrix2D(tuple(real_center), angle, scale)
    m[:, 2] += target_center - real_center  # rotate and scale about the real cube, then move onto the rendered one
    color = cv2.warpAffine(crop[..., :3].astype(np.float32) / 255, m, (w, h), flags=cv2.INTER_LINEAR)
    alpha = cv2.warpAffine(crop[..., 3].astype(np.float32) / 255, m, (w, h), flags=cv2.INTER_LINEAR)
    if shadow is not None:  # soft shadow: the hands' shape, shifted away from the light, blurred (at 1/4 size)
        size = tx1 - tx0
        d = np.asarray(shadow, float) / (np.linalg.norm(shadow) + 1e-6) * size * rng.uniform(0.03, 0.1) / 4
        small = cv2.resize(alpha, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        small = cv2.warpAffine(small, np.float32([[1, 0, d[0]], [0, 1, d[1]]]), (w // 4, h // 4))
        small = cv2.GaussianBlur(small, (0, 0), size * 0.015 + 0.5)
        canvas *= (1 - rng.uniform(0.25, 0.55) * cv2.resize(small, (w, h)))[..., None]
    canvas *= 1 - alpha[..., None]
    canvas += color * alpha[..., None]
    return alpha


def extract(clips, out: Path, every: int = 3, min_cube_score: float = 0.3, min_hand_score: float = 0.15) -> None:
    import torch
    from transformers import SamModel, SamProcessor

    from cubetrack.vision.detect import MODELS_DIR, OwlDetector, best

    hand_detector, cube_detector = OwlDetector("a human hand"), OwlDetector()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = SamProcessor.from_pretrained("facebook/sam-vit-base", cache_dir=MODELS_DIR / "hf")
    sam = SamModel.from_pretrained("facebook/sam-vit-base", cache_dir=MODELS_DIR / "hf").to(device).eval()
    out.mkdir(parents=True, exist_ok=True)
    entries, skipped = [], 0
    for clip in map(Path, clips):
        cap = cv2.VideoCapture(str(clip))
        index = -1
        while True:
            ok, frame = cap.read()
            index += 1
            if not ok:
                break
            if index % every:
                continue
            cube = best(cube_detector.detect(frame, min_cube_score))
            hands = sorted(hand_detector.detect(frame, min_hand_score), key=lambda d: -d.score)[:4]
            if not cube or not hands:
                skipped += 1
                continue
            inputs = processor(images=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), input_boxes=[[list(map(float, d.box))
                               for d in hands]], return_tensors="pt").to(device)
            with torch.no_grad():
                pred = sam(**inputs, multimask_output=False)
            masks = processor.image_processor.post_process_masks(
                pred.pred_masks.cpu(), inputs["original_sizes"].cpu(), inputs["reshaped_input_sizes"].cpu())[0][:, 0]
            mask = masks.numpy().any(0)
            x0, y0, x1, y1 = cube.box
            sam_area = mask.sum()
            mask = _drop_cube_pixels(frame, mask, cube.box)
            if mask.sum() < 0.2 * (x1 - x0) * (y1 - y0) or mask.sum() < 0.75 * sam_area:
                skipped += 1  # hands barely visible, or SAM's mask was largely not hand (shirt, arm, cube)
                continue
            bw, bh = x1 - x0, y1 - y0
            cx0, cy0 = max(int(x0 - MARGIN * bw), 0), max(int(y0 - MARGIN * bh), 0)
            cx1, cy1 = min(int(x1 + MARGIN * bw), frame.shape[1]), min(int(y1 + MARGIN * bh), frame.shape[0])
            alpha = cv2.GaussianBlur(mask.astype(np.float32), (3, 3), 0)  # soften the cut edge by a pixel
            crop = np.dstack([frame, (alpha * 255).astype(np.uint8)])[cy0:cy1, cx0:cx1]
            name = f"hand_{len(entries):05d}.png"
            cv2.imwrite(str(out / name), crop)
            entries.append({"file": name, "cube_box": [x0 - cx0, y0 - cy0, x1 - cx0, y1 - cy0], "source": clip.name,
                            "frame": index, "cube_score": round(cube.score, 3),
                            "hand_scores": [round(d.score, 3) for d in hands]})
        cap.release()
    (out / "index.json").write_text(json.dumps({"version": 1, "sam": "facebook/sam-vit-base", "every": every,
                                                "clips": [Path(c).name for c in clips], "hands": entries}, indent=1))
    print(f"saved {len(entries)} hand crops to {out} ({skipped} frames skipped)")


def _drop_cube_pixels(frame: np.ndarray, mask: np.ndarray, box) -> np.ndarray:
    """Remove what SAM let into the hand mask that is not hand: slivers of the real cube, shirt.

    The hands' own color is learned from mask pixels well away from the cube (clean skin); a pixel
    stays only if its chroma (Lab a, b) is close to that. Tile colors are far more saturated, white
    tiles far less, the red shirt redder, so they drop out. Small holes are filled, specks removed.
    """
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    near = np.zeros_like(mask)
    near[max(int(y0 - 0.25 * bh), 0):int(y1 + 0.25 * bh), max(int(x0 - 0.25 * bw), 0):int(x1 + 0.25 * bw)] = True
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.float32)
    clean = mask & ~near
    if clean.sum() < 200:
        return mask & ~near  # no clean skin to learn from: keep only the hands away from the cube
    ab = lab[..., 1:][clean]
    center = np.median(ab, 0)
    spread = np.median(np.abs(ab - center), 0) * 1.4826 + 2.0  # robust standard deviation, floored
    skin_like = (np.abs(lab[..., 1:] - center) < 3.5 * spread).all(-1) & (lab[..., 0] < 235)
    keep = (mask & skin_like).astype(np.uint8)  # everywhere: also drops shirt or background SAM included
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) & mask  # fill nail / highlight holes
    keep = cv2.morphologyEx(keep, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(keep)
    big = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 0.05 * bw * bh]  # drop specks
    return np.isin(labels, big)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--clips", nargs="+", required=True)
    parser.add_argument("--out", type=Path, default=Path("data") / "hands")
    parser.add_argument("--every", type=int, default=3, help="use every n-th frame")
    args = parser.parse_args(argv)
    extract(args.clips, args.out, args.every)


if __name__ == "__main__":
    main()
