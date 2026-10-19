"""Detector plumbing that needs no model weights. Detection quality itself is measured on recordings,
not here (pretrained models are not part of the camera-free test suite, docs/testing.md)."""
import numpy as np
import pytest

from cubetrack.ui.detect_check import describe, draw
from cubetrack.vision.detect import Detection, best, make_detector


def test_best_picks_the_highest_score_or_none():
    a, b = Detection((0, 0, 5, 5), 0.3, "cube"), Detection((1, 1, 9, 9), 0.7, "cube")
    assert best([a, b]) is b
    assert best([]) is None


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="owl"):
        make_detector("nope")


def test_drawing_and_text_handle_empty_and_nonempty_results():
    img = np.zeros((100, 100, 3), np.uint8)
    draw(img, [], "status")
    draw(img, [Detection((10, 10, 50, 50), 0.8, "cube"), Detection((20, 20, 60, 60), 0.3, "cube")], "status")
    assert img[40, 10].tolist() == [0, 255, 0]  # best box's left edge drawn green
    assert "no detections" in describe([])
    assert "0.80" in describe([Detection((10, 10, 50, 50), 0.8, "cube")])
