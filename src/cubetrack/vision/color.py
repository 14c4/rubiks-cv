"""Sticker color classification with a confidence for every sample.

Input is OpenCV 8-bit Lab (L 0-255, a and b centered on 128), one row per sticker sample.

How it works:
  1. Each sample becomes a feature vector (w * ln L*, s * a*/L*, s * b*/L*). Dividing the color part
     (a*, b*) by lightness L* makes it nearly shadow-proof: a shadow dims a sticker, which shrinks L*
     and a*/b* together, so their ratio barely moves. Lightness itself only enters as a small log term.
  2. Calibration stores one prototype (mean feature vector) per cube color, measured from the actual
     cube. Each face's center is also stored separately, because centers can carry a logo; only
     center cells are compared with those center prototypes.
  3. A sample's score for each color is a Gaussian of its distance to that prototype:
     exp(-d^2 / (2 sigma^2)). An extra "unknown" option scores as if it sat at distance
     `reject_sigmas * sigma`. Normalizing the seven scores gives probabilities.
  4. The predicted label is the most probable option; confidence is its probability. A sample far
     from every prototype (a hand, glare), too dark to judge, or flagged uneven by the caller is
     labelled None, with the reason, instead of being forced into the nearest color.

numpy only: no OpenCV here, so this can be tested and reused without a camera.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

COLORS = ("white", "yellow", "red", "orange", "green", "blue")
FORMAT_VERSION = 2

# Constants chosen on sessions 2026-10-18a/b plus simulated dimming (see D-008). A higher sigma floor or
# reject distance tolerates more shadow but starts accepting pale skin as white.
L_LOG_WEIGHT = 3.0  # weight of ln(L*): lightness still helps a little, but a shadow moves it only slightly
CHROMA_SCALE = 40.0  # scale of a*/L* and b*/L* so they are comparable to the log term
MIN_SIGMA = 3.0  # floor on the spread, in feature units, so a very tidy calibration is not overconfident
REJECT_SIGMAS = 3.75  # samples about this many sigmas from every prototype become "unknown"
DARK_FRACTION = 0.35  # samples darker than this fraction of the darkest calibrated sticker are "too dark"


def lightness(lab8) -> np.ndarray:
    """L* (0-100) from OpenCV 8-bit Lab, shape (...)."""
    return np.asarray(lab8, dtype=float)[..., 0] * (100.0 / 255.0)


def lab8_to_features(lab8, l_log_weight: float = L_LOG_WEIGHT, chroma_scale: float = CHROMA_SCALE) -> np.ndarray:
    """(..., 3) OpenCV 8-bit Lab -> (..., 3) features (w ln L*, s a*/L*, s b*/L*)."""
    lab = np.asarray(lab8, dtype=float)
    l_star = np.maximum(lightness(lab), 1.0)  # floor avoids dividing by ~0 on black pixels
    out = np.empty_like(lab)
    out[..., 0] = l_log_weight * np.log(l_star)
    out[..., 1] = chroma_scale * (lab[..., 1] - 128.0) / l_star
    out[..., 2] = chroma_scale * (lab[..., 2] - 128.0) / l_star
    return out


@dataclass(frozen=True)
class ColorEstimate:
    """What the classifier concluded about one sticker sample."""

    label: str | None  # one of COLORS, or None when the sample cannot be trusted as any color
    confidence: float  # probability of the best option (a color or "unknown"), 0-1
    probabilities: dict[str, float]  # every color plus "unknown"; sums to 1
    distance_sigmas: float  # distance to the nearest prototype, in units of sigma
    reason: str | None = None  # why label is None: "no_match", "too_dark" or "uneven"

    def runner_up(self) -> tuple[str, float]:
        """The second most likely option, useful for showing what the classifier was torn between."""
        ranked = sorted(self.probabilities.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[1]


@dataclass
class ColorModel:
    """One prototype per color (plus optional center-only prototypes) and a shared spread, in feature space."""

    prototypes: dict[str, np.ndarray]
    sigma: float
    min_lightness: float  # L* of the darkest calibrated sticker sample
    center_prototypes: dict[str, np.ndarray] = field(default_factory=dict)
    l_log_weight: float = L_LOG_WEIGHT
    chroma_scale: float = CHROMA_SCALE
    reject_sigmas: float = REJECT_SIGMAS
    dark_fraction: float = DARK_FRACTION

    @classmethod
    def fit(cls, samples: dict[str, np.ndarray], centers: dict[str, np.ndarray] | None = None,
            min_sigma: float = MIN_SIGMA) -> ColorModel:
        """Build a model from labelled 8-bit Lab samples.

        samples: {color: (N, 3)} non-center cells; all six colors required.
        centers: optional {color: (M, 3)} center cells of each face (may look different: logos).
        """
        missing = [c for c in COLORS if c not in samples or len(samples[c]) == 0]
        if missing:
            raise ValueError(f"calibration is missing samples for: {', '.join(missing)}")
        prototypes, squared_residuals, darkest = {}, [], np.inf
        for color in COLORS:
            lab = np.asarray(samples[color], dtype=float).reshape(-1, 3)
            feats = lab8_to_features(lab)
            prototypes[color] = feats.mean(axis=0)
            squared_residuals.append(((feats - prototypes[color]) ** 2).sum(axis=1))
            darkest = min(darkest, float(lightness(lab).min()))
        # pooled spread: root mean squared distance to own prototype, per dimension
        sigma = float(np.sqrt(np.concatenate(squared_residuals).mean() / 3))
        center_prototypes = {c: lab8_to_features(np.asarray(v, dtype=float).reshape(-1, 3)).mean(axis=0)
                             for c, v in (centers or {}).items() if len(v)}
        return cls(prototypes, max(sigma, min_sigma), darkest, center_prototypes)

    def classify(self, lab8, centers=None, uneven=None) -> list[ColorEstimate]:
        """Classify (N, 3) 8-bit Lab samples (any shape ending in 3 is flattened row-major).

        centers: optional (N,) bool, True where the sample is a face center (may match center prototypes).
        uneven: optional (N,) bool, True where the caller saw a non-uniform sampling box (edge, gap, glare).
        """
        lab = np.asarray(lab8, dtype=float).reshape(-1, 3)
        n = len(lab)
        centers = np.zeros(n, bool) if centers is None else np.asarray(centers, bool)
        uneven = np.zeros(n, bool) if uneven is None else np.asarray(uneven, bool)

        feats = lab8_to_features(lab, self.l_log_weight, self.chroma_scale)
        protos = np.stack([self.prototypes[c] for c in COLORS])  # (6, 3)
        d = np.linalg.norm(feats[:, None, :] - protos[None, :, :], axis=2) / self.sigma  # (N, 6) in sigmas
        for j, color in enumerate(COLORS):
            if color in self.center_prototypes:  # centers: a color matches if either of its prototypes does
                dc = np.linalg.norm(feats - self.center_prototypes[color], axis=1) / self.sigma
                d[:, j] = np.where(centers, np.minimum(d[:, j], dc), d[:, j])

        # log-scores: colors from their distance, "unknown" from the fixed reject distance
        logits = np.concatenate([-0.5 * d**2, np.full((n, 1), -0.5 * self.reject_sigmas**2)], axis=1)
        logits -= logits.max(axis=1, keepdims=True)  # stability: exp of large negatives underflows to 0
        probs = np.exp(logits)
        probs /= probs.sum(axis=1, keepdims=True)

        too_dark = lightness(lab) < self.dark_fraction * self.min_lightness
        names = (*COLORS, "unknown")
        results = []
        for i in range(n):
            best = int(probs[i].argmax())
            label = None if names[best] == "unknown" else names[best]
            if too_dark[i]:
                label, reason = None, "too_dark"
            elif uneven[i]:
                label, reason = None, "uneven"
            else:
                reason = "no_match" if label is None else None
            results.append(ColorEstimate(label, float(probs[i, best]), {k: float(p) for k, p in zip(names, probs[i])},
                                         float(d[i].min()), reason))
        return results

    def to_dict(self) -> dict:
        return {"version": FORMAT_VERSION, "sigma": self.sigma, "min_lightness": self.min_lightness,
                "prototypes": {c: p.tolist() for c, p in self.prototypes.items()},
                "center_prototypes": {c: p.tolist() for c, p in self.center_prototypes.items()},
                "l_log_weight": self.l_log_weight, "chroma_scale": self.chroma_scale,
                "reject_sigmas": self.reject_sigmas, "dark_fraction": self.dark_fraction}

    @classmethod
    def from_dict(cls, data: dict) -> ColorModel:
        if data.get("version") != FORMAT_VERSION:
            raise ValueError("calibration format changed; recalibrate (press C in the app)")
        return cls({c: np.array(p) for c, p in data["prototypes"].items()}, data["sigma"], data["min_lightness"],
                   {c: np.array(p) for c, p in data["center_prototypes"].items()},
                   data["l_log_weight"], data["chroma_scale"], data["reject_sigmas"], data["dark_fraction"])

    def save(self, path: str | Path, extra: dict | None = None) -> None:
        """Write the model as JSON; `extra` adds other keys (the app stores its grid geometry there)."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({**self.to_dict(), **(extra or {})}, indent=1))

    @classmethod
    def load(cls, path: str | Path) -> ColorModel:
        return cls.from_dict(json.loads(Path(path).read_text()))
