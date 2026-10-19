"""Synthetic renderer checks (roadmap 2.1).

Expected values come from docs/conventions.md (how each face is read), from the independent
RubikTwoPhase fixture states, and from hand-derived geometry; never from the renderer itself.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from cubetrack.cube import validate_facelets
from cubetrack.cube.facelets import idx
from cubetrack.synth.generate import main as generate_main, make_frame
from cubetrack.synth.render import Camera, Light, Look, Pose, REAL_BGR, draw_cube, frame_labels, look_at
from cubetrack.synth.scene import Backgrounds

CASES = json.loads((Path(__file__).parent / "fixtures" / "cube" / "reference_sequences.json").read_text())["cases"]
COLOR = {"U": "white", "R": "red", "F": "green", "D": "yellow", "L": "orange", "B": "blue"}  # D-004
NORMAL = {"U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1), "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1)}
# docs/conventions.md: the face whose edge is at the top of each face as it is read.
TOP = {"U": "B", "R": "U", "F": "U", "D": "F", "L": "U", "B": "U"}


def corner_view(a, b, c, up, distance=16.0):
    """Camera looking at the cube corner shared by faces a, b, c (so exactly those three show)."""
    toward = sum(np.array(NORMAL[f], float) for f in (a, b, c))
    z = -toward / np.linalg.norm(toward)
    y = -np.array(NORMAL[up], float)
    y -= z * (y @ z)
    y /= np.linalg.norm(y)
    return Pose(np.stack([np.cross(y, z), y, z]), np.array([0.0, 0.0, distance]))


def tiles(labels):
    return {t["name"]: t for face in labels["faces"] for t in face["tiles"]}


@pytest.mark.parametrize("face", "URFDLB")
def test_face_seen_straight_on_reads_like_the_conventions(face):
    labels = frame_labels("".join(f * 9 for f in "URFDLB"), Camera(), look_at(face, TOP[face]))
    assert [f["face"] for f in labels["faces"]] == [face]
    t = {n: np.array(v["center"]) for n, v in tiles(labels).items()}
    one, three, seven = t[f"{face}1"], t[f"{face}3"], t[f"{face}7"]
    assert one[0] < three[0] and abs(one[1] - three[1]) < 1e-6  # 1 -> 3 runs left to right
    assert one[1] < seven[1] and abs(one[0] - seven[0]) < 1e-6  # 1 -> 7 runs top to bottom
    assert sum(c["visible"] for c in labels["corners"]) == 4


@pytest.mark.parametrize("view", [("U", "R", "F", "U"), ("D", "B", "L", "B")])
@pytest.mark.parametrize("case", CASES[:18:3] + CASES[30:34], ids=lambda c: c["sequence"][:20])
def test_pixels_at_labelled_tiles_show_the_fixture_colors(case, view):
    # Plain render (gray background, light from the camera, no hands, no effects). The color at each
    # labelled tile center must be the fixture's color: a texture turned or mirrored would fail.
    cam, pose = Camera(), corner_view(*view)
    canvas = np.full((cam.height * 2, cam.width * 2, 3), 0.5, np.float32)
    draw_cube(canvas, case["facelets"], cam, pose, Look(), Light(position=np.zeros(3)), ss=2)
    img = canvas.reshape(cam.height, 2, cam.width, 2, 3).mean(axis=(1, 3))
    labels = frame_labels(case["facelets"], cam, pose)
    assert sorted(f["face"] for f in labels["faces"]) == sorted(view[:3])
    chroma = {c: np.array(v, float) / sum(v) for c, v in REAL_BGR.items()}
    for name, t in tiles(labels).items():
        if name.endswith("5"):
            continue  # centers carry the logo on white; they never move anyway
        x, y = np.round(t["center"]).astype(int)
        pixel = img[y - 1:y + 2, x - 1:x + 2].reshape(-1, 3).mean(0)
        nearest = min(chroma, key=lambda c: np.linalg.norm(pixel / pixel.sum() - chroma[c]))
        assert nearest == COLOR[case["facelets"][idx(name)]], name


def test_outlines_run_clockwise_from_the_reading_top_left():
    # Seen from outside, reading order TL -> TR -> BR -> BL goes clockwise; with image y pointing down
    # that is a positive shoelace area.
    for i in range(10):
        _, labels = make_frame(11, i)
        for face in labels["faces"]:
            x, y = np.array(face["outline"]).T
            assert np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)) > 0


def test_occluder_marks_covered_tiles_and_corners():
    # F straight on, everything left of the image center covered: the left column is hidden, the
    # middle column half, the right column fully visible.
    cam = Camera()
    occluder = np.zeros((cam.height, cam.width), np.float32)
    occluder[:, : cam.width // 2] = 1
    labels = frame_labels("".join(f * 9 for f in "URFDLB"), cam, look_at("F", "U"), occluder)
    vis = {n: t["visible"] for n, t in tiles(labels).items()}
    assert vis["F1"] == vis["F4"] == vis["F7"] == 0
    assert all(0.4 < vis[n] < 0.6 for n in ("F2", "F5", "F8"))
    assert vis["F3"] == vis["F6"] == vis["F9"] == 1
    occluded = {c["name"] for c in labels["corners"] if c["visible"] and c["occluded"]}
    assert occluded == {"UFL", "DLF"}  # F's two left corners


def test_sampled_frames_are_consistent():
    for i in range(20):
        img, labels = make_frame(7, i)
        assert img.shape == (480, 640, 3) and img.dtype == np.uint8
        assert validate_facelets(labels["facelets"]).status == "valid"
        faces = labels["faces"]
        assert 1 <= len(faces) <= 3
        # One face shows 4 cube corners, two neighboring faces 6, three faces 7.
        assert sum(c["visible"] for c in labels["corners"]) == {1: 4, 2: 6, 3: 7}[len(faces)]
        for face in faces:
            assert face["color"] == COLOR[face["face"]]
            for t in face["tiles"]:
                assert t["label"] == labels["facelets"][t["facelet"]] and t["color"] == COLOR[t["label"]]
                assert 0 <= t["visible"] <= 1


def test_same_seed_and_index_give_the_same_frame():
    a, la = make_frame(3, 5)
    b, lb = make_frame(3, 5)
    c, _ = make_frame(3, 6)
    assert np.array_equal(a, b) and la == lb
    assert not np.array_equal(a, c)


def test_dataset_writer(tmp_path):
    generate_main(["--out", str(tmp_path), "--count", "3", "--seed", "2", "--workers", "1"])
    assert sorted(p.name for p in (tmp_path / "images").iterdir()) == ["000000.jpg", "000001.jpg", "000002.jpg"]
    labels = json.loads((tmp_path / "labels" / "000001.json").read_text())
    assert labels["image"] == "images/000001.jpg" and labels["faces"]
    assert json.loads((tmp_path / "meta.json").read_text())["count"] == 3


def test_real_backgrounds_are_loaded_and_resized(tmp_path):
    import cv2
    cv2.imwrite(str(tmp_path / "bg.png"), np.full((100, 200, 3), 77, np.uint8))
    bg = Backgrounds([tmp_path], (640, 480))
    assert len(bg.frames) == 1
    sample = bg.sample(np.random.default_rng(0))
    assert sample.shape == (480, 640, 3) and np.all(sample == 77)


# ---------- real hands (D-014) ----------

def _crop_with_hand():
    """100x100 BGRA crop: real cube box (30, 30)-(70, 70), a 10x10 'hand' at x 0-10, y 45-55."""
    crop = np.zeros((100, 100, 4), np.uint8)
    crop[45:55, 0:10] = (60, 90, 140, 255)
    return crop


def test_pasted_hands_follow_the_cube_box():
    from cubetrack.synth.hands import paste_hands
    # Rendered cube box (100, 100)-(180, 180) is twice the real one, so the hand lands at
    # x = 100 + 2 * (0 - 30) = 40 .. 60, y = 100 + 2 * (45 - 30) = 130 .. 150.
    canvas = np.zeros((400, 400, 3), np.float32)
    alpha = paste_hands(np.random.default_rng(0), canvas, _crop_with_hand(), (30, 30, 70, 70), (100, 100, 180, 180),
                        jitter=False)
    ys, xs = np.nonzero(alpha > 0.5)
    found = np.array([xs.min(), xs.max(), ys.min(), ys.max()])
    assert np.abs(found - [40, 59, 130, 149]).max() <= 1  # within a pixel (pixel-center vs edge conventions)
    assert np.allclose(canvas[140, 50], np.array([60, 90, 140]) / 255, atol=0.01)


def test_real_hands_hide_tiles_in_the_labels(tmp_path):
    import cv2
    from cubetrack.synth.hands import HandLibrary
    from cubetrack.synth.scene import sample_frame
    crop = np.zeros((100, 100, 4), np.uint8)
    crop[20:80, 20:80] = (60, 90, 140, 255)  # a 'hand' covering the whole real cube box
    cv2.imwrite(str(tmp_path / "hand_00000.png"), crop)
    (tmp_path / "index.json").write_text(json.dumps({"hands": [{"file": "hand_00000.png", "cube_box": [30, 30, 70, 70]}]}))
    library = HandLibrary(tmp_path)
    for seed in range(10):
        _, labels = sample_frame(np.random.default_rng(seed), "".join(f * 9 for f in "URFDLB"), hand_library=library)
        if labels["render"]["hands"] == "real":
            break
    shown = [t["visible"] for face in labels["faces"] for t in face["tiles"]]
    assert labels["render"]["hands"] == "real" and np.mean(shown) < 0.5
