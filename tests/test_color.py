"""Color classifier checks against two real, independently labelled sessions.

Labels come from the owner (which solved face was shown), never from the classifier. Constants were
chosen looking at both sessions (D-008), so these are regression checks; the recorded lighting
sessions of Part B are the next held-out test.
"""
import json

import cv2
import numpy as np
import pytest

from cubetrack.evaluation.color_eval import (CENTER, CENTER_MASK, CONFIDENT, DEFAULT_FIXTURES as FIXTURES, FOREIGN,
                                             bgr_to_lab8, calibrate, load_session, score)
from cubetrack.ui.color_check import predict
from cubetrack.vision.color import COLORS, ColorModel
from cubetrack.vision.grid import GuideGrid

SESSIONS = [("2026-10-18a", "2026-10-18b"), ("2026-10-18b", "2026-10-18a")]


@pytest.mark.parametrize("train,test", SESSIONS)
def test_other_session_is_classified_correctly_and_confidently(train, test):
    faces = load_session(test)
    counts = score(calibrate(load_session(train)), faces)
    assert counts["wrong"] == 0 and counts["unknown"] == 0, counts
    assert counts["ok"] >= 0.95 * 9 * len(faces), counts


@pytest.mark.parametrize("train,test", SESSIONS)
def test_mild_shadow_keeps_nearly_all_cells_confident(train, test):
    """20% dimmer than the calibration light: the owner's desk-shadow complaint, simulated."""
    faces = load_session(test)
    counts = score(calibrate(load_session(train)), faces, dim=0.8)
    assert counts["wrong"] == 0, counts
    assert counts["ok"] >= 0.9 * 9 * len(faces), counts


@pytest.mark.parametrize("train,test", SESSIONS)
@pytest.mark.parametrize("dim", [0.6, 0.5])
def test_deep_shadow_never_produces_a_wrong_color(train, test, dim):
    counts = score(calibrate(load_session(train)), load_session(test), dim=dim)
    assert counts["wrong"] == 0, counts


def test_logo_center_reads_as_white():
    model = calibrate(load_session("2026-10-18a"))
    for face in load_session("2026-10-18b"):
        if face.label == "white" and face.pose == "flat":
            est = model.classify(bgr_to_lab8(face.bgr), centers=CENTER_MASK)[CENTER]
            assert est.label == "white" and est.confidence >= CONFIDENT, est


def test_logo_prototype_only_applies_to_the_center_cell():
    model = calibrate(load_session("2026-10-18a"))
    logo = bgr_to_lab8([next(f for f in load_session("2026-10-18b") if f.label == "white").bgr[CENTER]])
    as_center = model.classify(logo, centers=[True])[0]
    elsewhere = model.classify(logo)[0]  # same pinkish sample in a non-center cell: no logo prototype
    assert as_center.label == "white" and as_center.confidence >= CONFIDENT
    assert elsewhere.label is None or elsewhere.confidence < CONFIDENT


@pytest.mark.parametrize("name", ["dark table", "dark skin"])
def test_dark_things_are_unknown(name):
    model = calibrate(load_session("2026-10-18a"))
    assert model.classify(bgr_to_lab8([FOREIGN[name]]))[0].label is None


@pytest.mark.parametrize("train", ["2026-10-18a", "2026-10-18b"])
def test_light_skin_is_not_a_confident_color(train):
    """Known weakness (D-008): pale skin sits near white once lightness matters less; it must at least be uncertain."""
    model = calibrate(load_session(train))
    est = model.classify(bgr_to_lab8([FOREIGN["light skin"]]))[0]
    assert est.label is None or est.confidence < CONFIDENT


def test_too_dark_gate_and_reason():
    model = calibrate(load_session("2026-10-18a"))
    est = model.classify(bgr_to_lab8([(10, 10, 60)]))[0]  # a very dark red
    assert est.label is None and est.reason == "too_dark"


def test_uneven_cells_are_not_trusted():
    model = calibrate(load_session("2026-10-18a"))
    lab = bgr_to_lab8(load_session("2026-10-18b")[2].bgr)
    est = model.classify(lab, uneven=np.arange(9) == 0)
    assert est[0].label is None and est[0].reason == "uneven"
    assert all(e.reason is None for e in est[1:])


def test_halfway_between_red_and_orange_is_uncertain():
    model = calibrate(load_session("2026-10-18a"))
    red, orange = np.array([25, 32, 205]), np.array([0, 95, 242])  # typical BGR from session a
    est = model.classify(bgr_to_lab8([(red + orange) / 2]))[0]
    assert est.label is None or est.confidence < CONFIDENT


def test_probabilities_sum_to_one_and_include_unknown():
    model = calibrate(load_session("2026-10-18a"))
    for est in model.classify(bgr_to_lab8(load_session("2026-10-18b")[0].bgr)):
        assert set(est.probabilities) == {*COLORS, "unknown"}
        assert sum(est.probabilities.values()) == pytest.approx(1.0)


def test_fit_rejects_incomplete_calibration():
    samples = {c: np.full((8, 3), 128) for c in COLORS if c != "blue"}
    with pytest.raises(ValueError, match="blue"):
        ColorModel.fit(samples)


def test_save_and_load_give_identical_predictions(tmp_path):
    model = calibrate(load_session("2026-10-18a"))
    model.save(tmp_path / "m.json", extra={"grid": [1, 2, 3, 4]})
    loaded = ColorModel.load(tmp_path / "m.json")
    lab = bgr_to_lab8(load_session("2026-10-18b")[0].bgr)
    assert loaded.classify(lab, centers=CENTER_MASK) == model.classify(lab, centers=CENTER_MASK)
    assert loaded.center_prototypes.keys() == set(COLORS)


def test_old_calibration_format_is_rejected(tmp_path):
    (tmp_path / "old.json").write_text(json.dumps({"prototypes": {}, "sigma": 4, "l_weight": 0.5, "reject_sigmas": 4}))
    with pytest.raises(ValueError, match="recalibrate"):
        ColorModel.load(tmp_path / "old.json")


FRAMES = ["01_white", "02_yellow", "03_red", "04_orange", "05_green", "06_blue",
          "07_white_tilt_toward", "08_white_tilt_away"]


@pytest.mark.parametrize("frame_name", FRAMES)
def test_real_frames_through_the_full_pipeline(frame_name):
    """Raw camera frames (cropped to the grid) -> sampling -> Lab -> classifier, model from session a.

    Every cell is either the right color or explicitly flagged; never a different color.
    """
    model = calibrate(load_session("2026-10-18a"))
    frame = cv2.imread(str(FIXTURES / f"2026-10-18b_{frame_name}.png"))
    label = frame_name.split("_")[1]
    estimates = predict(GuideGrid.centered(frame.shape[1], frame.shape[0], fraction=1.0), model, frame)
    for i, est in enumerate(estimates):
        assert est.label in (label, None), f"cell {i}: got {est.label} ({est.confidence:.2f})"
    if "tilt" not in frame_name:  # flat faces: every cell, logo center included, is read
        assert [e.label for e in estimates] == [label] * 9


def test_tilted_face_flags_the_box_that_lands_on_a_gap():
    """In the tilt_toward frame the top-right box sits on the gap between stickers (seen in the image)."""
    model = calibrate(load_session("2026-10-18a"))
    frame = cv2.imread(str(FIXTURES / "2026-10-18b_07_white_tilt_toward.png"))
    estimates = predict(GuideGrid.centered(frame.shape[1], frame.shape[0], fraction=1.0), model, frame)
    assert estimates[2].reason == "uneven"
