"""Pretrained, text-prompted object detectors for finding the cube in a frame (no training needed).

Two backends behind one interface:
  - "owl":  OWLv2 (google/owlv2-base-patch16-ensemble, via transformers). Slower (~80 ms/frame on the
            RTX 4080 Super) but found the cube in all 8 saved test frames, scores 0.40-0.88.
  - "yolo": YOLO-World v2 x (via ultralytics). Fast (~11 ms/frame) but weak on this cube: scores
            0.02-0.40 and 3 of 8 test frames missed even at a 0.05 threshold.
Scores from the two are on different scales; each backend has its own default threshold.

Weights download once into models/ (git-ignored) and run locally afterwards.
torch / transformers / ultralytics are imported lazily so the rest of the package works without them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

MODELS_DIR = Path("models")
DEFAULT_PROMPT = "a photo of a rubik's cube"
DEFAULT_THRESHOLD = {"owl": 0.20, "yolo": 0.05}


@dataclass(frozen=True)
class Detection:
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 in frame pixels
    score: float  # the backend's own score (not a calibrated probability)
    label: str


class OwlDetector:
    name = "owl"

    def __init__(self, prompt: str = DEFAULT_PROMPT, model_id: str = "google/owlv2-base-patch16-ensemble"):
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor

        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = Owlv2Processor.from_pretrained(model_id, cache_dir=MODELS_DIR / "hf")
        self.model = Owlv2ForObjectDetection.from_pretrained(model_id, cache_dir=MODELS_DIR / "hf").to(self.device).eval()
        self.prompt = prompt

    def detect(self, frame: np.ndarray, threshold: float) -> list[Detection]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        side = max(frame.shape[:2])  # OWLv2 pads to a square at the bottom/right, so boxes map back 1:1
        inputs = self.processor(text=[[self.prompt]], images=rgb, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            outputs = self.model(**inputs)
        res = self.processor.post_process_grounded_object_detection(outputs, threshold=threshold,
                                                                   target_sizes=[(side, side)])[0]
        return [Detection(tuple(int(v) for v in box.tolist()), float(score), self.prompt)
                for box, score in zip(res["boxes"], res["scores"])]


class YoloWorldDetector:
    name = "yolo"

    def __init__(self, prompt: str = DEFAULT_PROMPT, weights: str = "yolov8x-worldv2.pt"):
        from ultralytics import YOLOWorld

        self.model = YOLOWorld(str(MODELS_DIR / weights))
        # YOLO-World matches short class names better than sentences
        self.prompt = prompt.removeprefix("a photo of ").removeprefix("a ")
        self.model.set_classes([self.prompt])

    def detect(self, frame: np.ndarray, threshold: float) -> list[Detection]:
        result = self.model.predict(frame, conf=threshold, verbose=False)[0]
        return [Detection(tuple(int(v) for v in b.xyxy[0].tolist()), float(b.conf), self.prompt) for b in result.boxes]


BACKENDS = {"owl": OwlDetector, "yolo": YoloWorldDetector}


def make_detector(backend: str, prompt: str = DEFAULT_PROMPT):
    if backend not in BACKENDS:
        raise ValueError(f"unknown detector {backend!r}; choose from {', '.join(BACKENDS)}")
    return BACKENDS[backend](prompt)


def best(detections: list[Detection]) -> Detection | None:
    """The highest-scoring detection (one cube is expected in view), or None."""
    return max(detections, key=lambda d: d.score, default=None)
