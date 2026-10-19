"""Random scenes around the owner's setup: a cube held up to a camera that faces them (capture-setup.md).

Everything is randomized widely (domain randomization): the model should find faces and tiles in any
of these variations, so that the real camera is just one more variation it has seen. Realism comes from
variety, not from exact physics (D-013).

sample_frame(rng, facelets) -> (BGR uint8 image, labels). Per frame:
  pose        any orientation, or one face turned toward the camera; mostly ~150 px across at chest
              height (measured in the owner's clips), sometimes 60-320 px anywhere
  look        tile colors jittered around the owner's measured colors, tile shape, gloss, a logo
  light       one point light in front of the cube (room light), random color and strength
  background  a real frame (if given) or a procedural room with a person in it
  hands       the owner's real hands cut out of a clip (synth/hands.py), or drawn shapes as a fallback
  camera      exposure, white balance, gradient light, motion blur, defocus, noise, JPEG
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from cubetrack.synth.render import CORNERS, Camera, Light, Look, Pose, REAL_BGR, COLOR_OF, draw_cube, frame_labels
from cubetrack.synth.render import look_at
from cubetrack.cube.facelets import FACES

SS = 2  # draw at twice the size, then shrink: smooth (antialiased) edges everywhere
OWNER_SKIN_BGR = (75, 89, 116)  # median of the owner's face in shade, background clip 2026-10-18
SKIN_BGR = [(170, 190, 230), (150, 175, 220), (120, 150, 200), (100, 135, 185), (80, 110, 160), (55, 80, 120)]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mkv", ".mov"}


# ---------- cube pose, look, light ----------

def random_rotation(rng: np.random.Generator) -> np.ndarray:
    """A rotation drawn uniformly over all orientations (a random unit quaternion)."""
    q = rng.normal(size=4)
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def small_rotation(rng: np.random.Generator, max_degrees: float) -> np.ndarray:
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    angle = math.radians(rng.uniform(0, max_degrees))
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * k @ k


def sample_pose(rng: np.random.Generator, cam: Camera) -> Pose:
    if rng.random() < 0.6:
        rotation = random_rotation(rng)  # usually shows three faces
    else:  # one face toward the camera, tilted: shows one or two faces, like showing a face off
        face = FACES[rng.integers(6)]
        up = rng.choice([u for u in FACES if u != face and FACES.index(u) % 3 != FACES.index(face) % 3])
        rotation = small_rotation(rng, 40) @ look_at(face, up).R
    if rng.random() < 0.7:  # the owner's setup: cube about 150 px wide at chest height (measured, see 2.1 log)
        width_px = float(np.clip(150 * math.exp(rng.normal(0, 0.25)), 60, 320))
        u = np.clip(rng.normal(0.57, 0.1), 0.1, 0.9) * cam.width
        v = np.clip(rng.normal(0.66, 0.1), 0.1, 0.9) * cam.height
    else:  # anything else: other distances, anywhere in the frame
        width_px = rng.uniform(60, 320)
        u, v = rng.uniform(0.12, 0.88) * cam.width, rng.uniform(0.12, 0.88) * cam.height
    distance = cam.f * 4.0 / width_px  # a cube seen at an angle spans about 4 cubies across (3 face-on, 4.2 edge-on)
    cx, cy = cam.center
    return Pose(rotation, np.array([(u - cx) * distance / cam.f, (v - cy) * distance / cam.f, distance]))


def random_logo(rng: np.random.Generator) -> list:
    """A few red strokes standing in for the printed logo on the white center."""
    strokes = []
    for _ in range(rng.integers(2, 6)):
        start = rng.uniform(0.25, 0.75, 2)
        pts = [start]
        for _ in range(rng.integers(1, 4)):
            pts.append(np.clip(pts[-1] + rng.normal(0, 0.15, 2), 0.2, 0.8))
        strokes.append(np.array(pts).tolist())
    return strokes


def sample_look(rng: np.random.Generator) -> Look:
    colors = {}
    for label in FACES:
        base = np.array(REAL_BGR[COLOR_OF[label]], float) / 255
        base = base * rng.uniform(0.8, 1.05) + rng.normal(0, 0.025, 3)  # this cube's version of the color
        colors[label] = tuple(np.clip(base, 0, 1))
    gray = rng.uniform(0.02, 0.1)
    return Look(colors=colors, body=tuple(np.clip(gray + rng.normal(0, 0.01, 3), 0, 1)),
                gap=rng.uniform(0.01, 0.04), seam_dark=rng.uniform(0.15, 0.55), seam_black=rng.uniform(0.0, 0.6),
                radius=rng.uniform(0.06, 0.2), bevel=rng.uniform(0.03, 0.1),
                bevel_angle=rng.uniform(0.4, 1.0), specular=rng.uniform(0.05, 0.5), shininess=rng.uniform(8, 60),
                logo=random_logo(rng) if rng.random() < 0.9 else [],
                logo_color=tuple(np.clip(np.array([0.12, 0.10, 0.78]) + rng.normal(0, 0.05, 3), 0, 1)),
                logo_width=rng.uniform(0.04, 0.09))


def sample_light(rng: np.random.Generator, pose: Pose) -> Light:
    # Somewhere in front of the cube (the camera side), usually above it: a room or desk light.
    direction = np.array([rng.uniform(-1, 1), rng.uniform(-1.2, 0.4), -rng.uniform(0.2, 1.0)])
    direction /= np.linalg.norm(direction)
    position = pose.t + direction * rng.uniform(6, 40)
    warm = rng.uniform(-1, 1)  # -1 cool (bluish), +1 warm (yellowish)
    color = np.array([1 - 0.15 * warm, 1.0, 1 + 0.12 * warm]) * rng.uniform(0.75, 1.25)
    return Light(position=position, color=tuple(color), ambient=rng.uniform(0.35, 0.75), diffuse=rng.uniform(0.35, 0.8))


# ---------- background ----------

class Backgrounds:
    """Real background frames (images and/or videos in the given paths), resized to the camera size."""

    def __init__(self, paths, size: tuple[int, int], frames_per_video: int = 120):
        self.frames = []
        files = []
        for p in map(Path, paths):
            files += sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in files:
            if f.suffix.lower() in IMAGE_SUFFIXES:
                img = cv2.imread(str(f))
                if img is not None:
                    self.frames.append(cv2.resize(img, size, interpolation=cv2.INTER_AREA))
            elif f.suffix.lower() in VIDEO_SUFFIXES:
                cap = cv2.VideoCapture(str(f))
                n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                for i in np.linspace(0, max(n - 1, 0), min(frames_per_video, max(n, 1))).astype(int):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
                    ok, img = cap.read()
                    if ok:
                        self.frames.append(cv2.resize(img, size, interpolation=cv2.INTER_AREA))
                cap.release()

    def sample(self, rng: np.random.Generator) -> np.ndarray:
        img = self.frames[rng.integers(len(self.frames))]
        h, w = img.shape[:2]
        scale = rng.uniform(0.7, 1.0)  # random crop, scaled back up
        ch, cw = int(h * scale), int(w * scale)
        y, x = rng.integers(0, h - ch + 1), rng.integers(0, w - cw + 1)
        out = cv2.resize(img[y:y + ch, x:x + cw], (w, h), interpolation=cv2.INTER_LINEAR)
        return out[:, ::-1].copy() if rng.random() < 0.5 else out


def _muted(rng, lo=40, hi=200) -> np.ndarray:
    gray = rng.uniform(lo, hi)
    return np.clip(gray + rng.normal(0, 25, 3), 0, 255)


def procedural_background(rng: np.random.Generator, width: int, height: int) -> np.ndarray:
    """A room with a person in it, seen by a camera facing them (blurred: the camera focuses on the cube)."""
    top, bottom = _muted(rng), _muted(rng)
    ramp = np.linspace(0, 1, height)[:, None, None]
    img = np.broadcast_to(top * (1 - ramp) + bottom * ramp, (height, width, 3)).astype(np.float32).copy()
    for _ in range(rng.integers(1, 7)):  # furniture, doors, shelves, a bright window
        x0, y0 = rng.integers(0, width), rng.integers(0, height)
        x1, y1 = x0 + rng.integers(20, width // 2), y0 + rng.integers(20, height // 2)
        color = _muted(rng, 200, 255) if rng.random() < 0.15 else _muted(rng)
        cv2.rectangle(img, (int(x0), int(y0)), (int(x1), int(y1)), color.tolist(), -1)
    if rng.random() < 0.85:  # the person: shirt, neck, face, hair
        skin = np.array(SKIN_BGR[rng.integers(len(SKIN_BGR))], float) * rng.uniform(0.7, 1.1)
        cx = int(width * rng.uniform(0.3, 0.7))
        face_h = int(height * rng.uniform(0.25, 0.5))
        face_y = int(height * rng.uniform(0.15, 0.45))
        shirt = _muted(rng, 20, 230) if rng.random() < 0.8 else rng.uniform(0, 255, 3)
        shirt_top = face_y + int(face_h * 0.75)
        cv2.ellipse(img, (cx, shirt_top + height), (int(width * rng.uniform(0.3, 0.6)), height), 0, 180, 360,
                    shirt.tolist(), -1)
        if rng.random() < 0.3:  # stripes or checks on the shirt
            stripe = np.clip(shirt + rng.uniform(-80, 80, 3), 0, 255)
            step = int(rng.integers(8, 30))
            mask = np.zeros((height, width), np.uint8)
            cv2.ellipse(mask, (cx, shirt_top + height), (int(width * 0.6), height), 0, 180, 360, 1, -1)
            lines = np.zeros_like(mask)
            for x in range(0, width + height, step):
                cv2.line(lines, (x, 0), (x - height, height), 1, max(2, step // 3))
            img[(mask & lines) > 0] = stripe
        cv2.rectangle(img, (cx - face_h // 6, face_y), (cx + face_h // 6, shirt_top + 5), (skin * 0.85).tolist(), -1)
        cv2.ellipse(img, (cx, face_y), (int(face_h * 0.38), face_h // 2), 0, 0, 360, skin.tolist(), -1)
        hair = np.clip(rng.uniform(10, 90) + rng.normal(0, 10, 3), 0, 255)
        cv2.ellipse(img, (cx, face_y - face_h // 5), (int(face_h * 0.42), int(face_h * 0.38)), 0, 180, 360,
                    hair.tolist(), -1)
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(1.5, 6))
    img += rng.normal(0, rng.uniform(1, 5), img.shape).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)


# ---------- hands ----------

def _finger(canvas, alpha, tip, base, width, color, nail=False):
    """A shaded, tapered finger from `tip` to `base`, drawn over `canvas` (float BGR 0..1) and into `alpha`."""
    h, w = alpha.shape
    x0, y0 = int(max(min(tip[0], base[0]) - width, 0)), int(max(min(tip[1], base[1]) - width, 0))
    x1, y1 = int(min(max(tip[0], base[0]) + width, w)), int(min(max(tip[1], base[1]) + width, h))
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ab = base - tip
    s = np.clip(((xs - tip[0]) * ab[0] + (ys - tip[1]) * ab[1]) / max(ab @ ab, 1e-6), 0, 1)  # 0 at the tip
    dist = np.hypot(xs - tip[0] - s * ab[0], ys - tip[1] - s * ab[1])
    radius = width / 2 * (0.8 + 0.2 * s)  # thinner toward the tip
    cover = np.clip(radius - dist + 0.5, 0, 1)
    profile = np.sqrt(np.clip(1 - (dist / radius) ** 2, 0, 1))  # round cross-section: darker at the sides
    rgb = np.array(color, np.float32)[None, None, :] * (0.45 + 0.55 * profile)[..., None]
    if nail:  # a paler, glossier patch at the tip
        tip_zone = np.clip(1 - s * np.linalg.norm(ab) / (1.1 * width), 0, 1) * (dist < radius * 0.6)
        rgb = rgb * (1 - 0.5 * tip_zone[..., None]) + np.float32([0.8, 0.82, 0.95]) * 0.5 * tip_zone[..., None]
    region = canvas[y0:y1, x0:x1]
    region[:] = region * (1 - cover[..., None]) + rgb * cover[..., None]
    alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], cover)


def _hand(rng, hull, center, size, d, skin, width, thumb_side):
    """One hand on side d of the cube: palm behind, 2-4 fingertips over that edge, maybe a thumb.

    thumb_side: "opposite" (one-handed grip: thumb on the far side), "below" (two-handed grip: thumb
    under the cube's front, near this hand's side) or None.
    """
    p = np.array([-d[1], d[0]])
    if p[1] < 0:
        p = -p  # p points down the image, toward the arm
    reach = max((hull - center) @ d)
    fingers = []
    n = int(rng.integers(2, 5))
    first = rng.uniform(-0.5, 0.0) * size
    for k in range(n):  # tips just over the cube's edge, knuckles beyond it
        o = first + k * width * rng.uniform(0.95, 1.1)
        tip = center + d * (reach - rng.uniform(0.0, 0.35) * size) + p * o
        base = tip + d * size * rng.uniform(0.35, 0.65) + p * size * rng.uniform(0.05, 0.3)
        fingers.append((tip, base, width * rng.uniform(0.9, 1.1)))
    if thumb_side == "opposite":
        far = max((hull - center) @ -d)
        tip = center - d * (far - rng.uniform(0.0, 0.45) * size) + p * rng.normal(0.1, 0.25) * size
        base = tip - d * size * rng.uniform(0.6, 1.0) + p * size * rng.uniform(0.3, 0.7)
        fingers.append((tip, base, width * rng.uniform(1.1, 1.35)))
    elif thumb_side == "below":
        low = max((hull - center) @ p)
        tip = center + p * (low - rng.uniform(0.0, 0.3) * size) + d * rng.uniform(0.05, 0.4) * size
        base = tip + p * size * rng.uniform(0.5, 0.9) + d * size * rng.uniform(0.2, 0.5)
        fingers.append((tip, base, width * rng.uniform(1.1, 1.35)))
    palm_at = center + d * reach * rng.uniform(0.4, 0.9) + p * rng.uniform(0.4, 0.8) * size  # behind, from below
    angle = math.degrees(math.atan2(d[1], d[0]))
    return {"fingers": fingers, "palm": (palm_at, (0.85 * size, 0.7 * size), angle), "skin": skin, "size": size}


def plan_hands(rng: np.random.Generator, hull: np.ndarray) -> list[dict]:
    """Hands holding the cube, as in the owner's clips: usually both hands, fingertips over the left
    and right edges and thumbs below; sometimes one hand (fingers one side, thumb the other); sometimes none."""
    r = rng.random()
    if r < 0.1:
        return []
    center = hull.mean(0)
    size = math.sqrt(max(cv2.contourArea(hull.astype(np.float32)), 1.0))
    if rng.random() < 0.5:  # the owner's tone (measured in shade, so usually brighter on the hands)
        skin = np.array(OWNER_SKIN_BGR, float) / 255 * rng.uniform(1.0, 1.5)
    else:
        skin = np.array(SKIN_BGR[rng.integers(len(SKIN_BGR))], float) / 255 * rng.uniform(0.75, 1.15)
    skin = np.clip(skin, 0, 1)
    width = size * rng.uniform(0.3, 0.42)  # fingers are wide next to a 5.6 cm cube
    angle = rng.normal(0, 0.35)  # grip roughly left-right
    d = np.array([math.cos(angle), math.sin(angle)])
    if r < 0.4:
        side = d if rng.random() < 0.5 else -d
        return [_hand(rng, hull, center, size, side, skin, width, "opposite" if rng.random() < 0.85 else None)]
    return [_hand(rng, hull, center, size, side, skin, width, "below" if rng.random() < 0.6 else None)
            for side in (d, -d)]


def draw_palm(canvas: np.ndarray, hand: dict | None) -> None:
    """The palm, behind the cube (drawn before it): an ellipse shaded like a rounded surface."""
    if not hand:
        return
    (cx, cy), (ax, ay), angle = hand["palm"]
    h, w = canvas.shape[:2]
    r = max(ax, ay) + 2
    x0, y0, x1, y1 = int(max(cx - r, 0)), int(max(cy - r, 0)), int(min(cx + r, w)), int(min(cy + r, h))
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    c, s_ = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    rho = np.hypot(((xs - cx) * c + (ys - cy) * s_) / ax, (-(xs - cx) * s_ + (ys - cy) * c) / ay)  # 1 on the rim
    mask = np.clip((1 - rho) * min(ax, ay) + 0.5, 0, 1)
    shade = np.sqrt(np.clip(1 - rho ** 2, 0, 1))
    color = hand["skin"].astype(np.float32) * (0.6 + 0.35 * shade)[..., None]
    region = canvas[y0:y1, x0:x1]
    region[:] = region * (1 - mask[..., None]) + color * mask[..., None]


def draw_fingers(rng: np.random.Generator, canvas: np.ndarray, hand: dict | None, light_dir: np.ndarray) -> np.ndarray:
    """Fingers and thumb in front of the cube, with soft shadows; returns their alpha (the occluder)."""
    alpha = np.zeros(canvas.shape[:2], np.float32)
    if not hand or not hand["fingers"]:
        return alpha
    size = hand["size"]
    # Soft shadow first: the fingers' shape, shifted away from the light and blurred, darkens what is below.
    shift = -light_dir[:2] / (np.linalg.norm(light_dir[:2]) + 1e-6) * size * rng.uniform(0.03, 0.12)
    sigma = size * 0.06 + 1
    pts = np.array([q + shift for tip, base, _ in hand["fingers"] for q in (tip, base)])
    pad = max(fw for *_, fw in hand["fingers"]) + 3 * sigma
    h, w = alpha.shape
    x0, y0 = int(max(pts[:, 0].min() - pad, 0)), int(max(pts[:, 1].min() - pad, 0))
    x1, y1 = int(min(pts[:, 0].max() + pad, w)), int(min(pts[:, 1].max() + pad, h))
    if x0 < x1 and y0 < y1:  # only the region around the hand
        shadow = np.zeros((y1 - y0, x1 - x0), np.float32)
        for tip, base, fw in hand["fingers"]:
            a, b = np.int32(tip + shift - (x0, y0)), np.int32(base + shift - (x0, y0))
            cv2.line(shadow, tuple(map(int, a)), tuple(map(int, b)), 1.0, max(int(fw), 1), cv2.LINE_AA)
        shadow = cv2.GaussianBlur(shadow, (0, 0), sigma)
        canvas[y0:y1, x0:x1] *= (1 - rng.uniform(0.25, 0.6) * shadow)[..., None]
    for tip, base, fw in hand["fingers"]:
        tone = np.clip(hand["skin"] * rng.uniform(0.92, 1.08), 0, 1)
        _finger(canvas, alpha, tip, base, fw, tone, nail=rng.random() < 0.5)
    return alpha


# ---------- camera effects ----------

def camera_effects(rng: np.random.Generator, img: np.ndarray) -> tuple[np.ndarray, int]:
    """float BGR 0..1 -> uint8 after exposure, white balance, uneven light, blur, noise; plus a JPEG quality."""
    h, w = img.shape[:2]
    img = img * rng.uniform(0.6, 1.25) * rng.uniform(0.85, 1.15, 3)  # exposure, white balance
    if rng.random() < 0.5:  # light falling off across the frame
        angle = rng.uniform(0, 2 * math.pi)
        ys, xs = np.mgrid[0:h, 0:w]
        ramp = (xs - w / 2) * math.cos(angle) + (ys - h / 2) * math.sin(angle)
        img = img * (1 - rng.uniform(0, 0.4) * (ramp / np.abs(ramp).max() + 1) / 2)[..., None]
    img = np.clip(img, 0, 1) ** rng.uniform(0.8, 1.25)
    if rng.random() < 0.5:  # motion blur: the cube moving during the exposure (strong when turning it)
        length = int(rng.integers(3, 26))
        kernel = np.zeros((length, length), np.float32)
        kernel[length // 2, :] = 1 / length
        rot = cv2.getRotationMatrix2D(((length - 1) / 2, (length - 1) / 2), rng.uniform(0, 180), 1)
        kernel = cv2.warpAffine(kernel, rot, (length, length))
        img = cv2.filter2D(img.astype(np.float32), -1, kernel / max(kernel.sum(), 1e-6))
    if rng.random() < 0.25:  # out of focus
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.5, 1.8))
    img = img * 255 + rng.normal(0, rng.uniform(1, 6), img.shape)
    return np.clip(img, 0, 255).astype(np.uint8), int(rng.integers(35, 96))


# ---------- one frame ----------

def sample_frame(rng: np.random.Generator, facelets: str, cam: Camera | None = None,
                 backgrounds: Backgrounds | None = None, effects: bool = True,
                 hand_library=None) -> tuple[np.ndarray, dict]:
    """One synthetic frame of the cube `facelets` and its labels (see render.frame_labels).

    With a hand library (synth/hands.py, D-014) the hands are the owner's real hands cut out of a clip;
    without one they are drawn (shaded shapes, a fallback)."""
    cam = cam or Camera(f=float(rng.uniform(430, 650)))
    pose = sample_pose(rng, cam)
    look, light = sample_look(rng), sample_light(rng, pose)
    if backgrounds and backgrounds.frames and rng.random() < 0.8:
        bg, bg_kind = backgrounds.sample(rng), "real"
    else:
        bg, bg_kind = procedural_background(rng, cam.width, cam.height), "procedural"
    canvas = cv2.resize(bg, (cam.width * SS, cam.height * SS), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
    corners = cam.project(pose.apply(1.5 * np.array(list(CORNERS.values()), float)))
    hull = cv2.convexHull(((corners + 0.5) * SS - 0.5).astype(np.float32)).reshape(-1, 2)
    real_hands = hand_library is not None and len(hand_library) > 0
    hands = [] if real_hands else plan_hands(rng, hull)
    for hand in hands:
        draw_palm(canvas, hand)
    draw_cube(canvas, facelets, cam, pose, look, light, SS)
    fingers = np.zeros(canvas.shape[:2], np.float32)
    for hand in hands:
        fingers = np.maximum(fingers, draw_fingers(rng, canvas, hand, light.position - pose.t))
    if real_hands and rng.random() < 0.9:
        box = (*hull.min(0), *hull.max(0))
        fingers = hand_library.paste(rng, canvas, box, shadow=-(light.position - pose.t)[:2])
    hand_kind = ("real" if real_hands else "drawn") if fingers.max() > 0 else "none"
    img = cv2.resize(canvas, (cam.width, cam.height), interpolation=cv2.INTER_AREA)
    occluder = cv2.resize(fingers, (cam.width, cam.height), interpolation=cv2.INTER_AREA)
    quality = 95
    if effects:
        img, quality = camera_effects(rng, img)
        img = cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])[1], cv2.IMREAD_COLOR)
    else:
        img = np.clip(img * 255, 0, 255).astype(np.uint8)
    labels = frame_labels(facelets, cam, pose, occluder)
    labels["render"] = {"background": bg_kind, "hands": hand_kind, "jpeg_quality": quality,
                        "effects": effects}
    return img, labels
