"""Draw a cube state as a camera would see it, with exact labels (roadmap 2.1, D-013).

Geometry comes from the engine (cube/moves.py GEOMETRY: each facelet's cubie position and outward
normal; x toward R, y toward U, z toward F; one cubie = 1 unit, so the cube spans -1.5..1.5). The drawn
cube therefore cannot disagree with the engine's conventions.

Camera: a pinhole. A point (X, Y, Z) in camera coordinates (x right, y down, z forward, OpenCV's
convention) lands on pixel (f X / Z + cx, f Y / Z + cy). A Pose turns cube coordinates into camera
coordinates: p_cam = R p_cube + t.

How a face is drawn:
  1. Paint it flat as a square texture: nine rounded tiles separated by thin seams, the logo on the
     white center. The owner's cube is stickerless (colored plastic pieces), so a seam shows a darker
     shade of the tile's own color plus a little of the black inside. Each texel is lit from its 3D
     position and normal; near a tile's rim the normal tilts outward, as the pieces are rounded.
  2. Project the face's four 3D corners into the image.
  3. Four corner pairs define a homography: the 3x3 matrix that maps a plane onto its perspective
     image. cv2.warpPerspective uses it to paste the texture exactly where the face appears.
Labels are the same projected 3D points, so they are exact by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from cubetrack.cube.facelets import FACES
from cubetrack.cube.moves import GEOMETRY
from cubetrack.vision.assemble import STANDARD_SCHEME

COLOR_OF = {label: color for color, label in STANDARD_SCHEME.items()}  # D-004
# Mean BGR of the owner's tiles, sessions 2026-10-18a/b (tests/fixtures/color), as 0..1 albedo.
REAL_BGR = {"white": (203, 218, 229), "yellow": (0, 220, 227), "red": (18, 27, 206),
            "orange": (0, 93, 240), "green": (43, 173, 43), "blue": (177, 96, 25)}
# Corner slots (docs/conventions.md order) and their position: letters name the three faces they touch.
CORNERS = {"URF": (1, 1, 1), "UFL": (-1, 1, 1), "ULB": (-1, 1, -1), "UBR": (1, 1, -1),
           "DFR": (1, -1, 1), "DLF": (-1, -1, 1), "DBL": (-1, -1, -1), "DRB": (1, -1, -1)}


def _face_frame(f: int):
    """Face f's top-left corner and unit vectors along its rows (right) and down its columns, as read
    in the standard view (docs/conventions.md), plus its outward normal; all in cube coordinates."""
    pos = np.array([GEOMETRY[9 * f + i][0] for i in range(9)], float)
    normal = np.array(GEOMETRY[9 * f][1], float)
    right, down = pos[1] - pos[0], pos[3] - pos[0]
    origin = pos[0] + 0.5 * normal - 0.5 * right - 0.5 * down
    return origin, right, down, normal


FACE_FRAMES = [_face_frame(f) for f in range(6)]


def face_point(f: int, u, v):
    """Cube coordinates of the point u cubies right and v cubies down from face f's top-left corner."""
    origin, right, down, _ = FACE_FRAMES[f]
    return origin + np.asarray(u, float)[..., None] * right + np.asarray(v, float)[..., None] * down


@dataclass(frozen=True)
class Camera:
    width: int = 640
    height: int = 480
    f: float = 520.0  # focal length in pixels (a phone's ~65 degree horizontal view at 640 wide)

    @property
    def center(self) -> tuple[float, float]:
        return (self.width - 1) / 2, (self.height - 1) / 2

    def project(self, p_cam) -> np.ndarray:
        p = np.asarray(p_cam, float)
        cx, cy = self.center
        return np.stack([self.f * p[..., 0] / p[..., 2] + cx, self.f * p[..., 1] / p[..., 2] + cy], axis=-1)


@dataclass
class Pose:
    R: np.ndarray  # rotation, cube -> camera
    t: np.ndarray  # cube center in camera coordinates

    def apply(self, p_cube) -> np.ndarray:
        return np.asarray(p_cube, float) @ self.R.T + self.t


def look_at(face: str, up: str, distance: float = 20.0) -> Pose:
    """The pose that shows `face` straight on with `up` at the top of the image, centered."""
    n = {label: np.array(GEOMETRY[9 * i][1], float) for i, label in enumerate(FACES)}
    z = -n[face]  # the camera looks into the face
    y = -n[up]  # image y points down, away from `up`
    x = np.cross(y, z)
    return Pose(np.stack([x, y, z]), np.array([0.0, 0.0, distance]))


@dataclass
class Look:
    """What this particular cube looks like."""
    colors: dict = field(default_factory=lambda: {label: tuple(c / 255 for c in REAL_BGR[COLOR_OF[label]])
                                                  for label in FACES})  # face label -> BGR albedo 0..1
    body: tuple = (0.07, 0.07, 0.08)  # dark inside of the cube, glimpsed through the seams
    gap: float = 0.025  # cubie units between a tile's edge and its cell's edge (half the seam)
    seam_dark: float = 0.35  # stickerless pieces are colored plastic: a seam shows the tile color, darker...
    seam_black: float = 0.3  # ...mixed with this much of the dark inside
    radius: float = 0.14  # tile corner radius
    bevel: float = 0.06  # width of the rounded rim
    bevel_angle: float = 0.8  # how far the rim's normal tilts at the very edge (radians)
    specular: float = 0.35
    shininess: float = 30.0
    logo: list = field(default_factory=list)  # polylines in center-tile coordinates 0..1, drawn on U's center
    logo_color: tuple = (0.12, 0.10, 0.78)
    logo_width: float = 0.06


@dataclass
class Light:
    position: np.ndarray  # camera coordinates
    color: tuple = (1.0, 1.0, 1.0)  # BGR gains
    ambient: float = 0.45
    diffuse: float = 0.65


def visible_faces(pose: Pose) -> list[int]:
    """Faces whose outside points toward the camera (back-face culling; the cube is convex)."""
    out = []
    for f, (_, _, _, normal) in enumerate(FACE_FRAMES):
        center = pose.apply(face_point(f, 1.5, 1.5))
        if np.dot(normal @ pose.R.T, center) < 0:
            out.append(f)
    return out


def face_texture(facelets: str, f: int, look: Look, light: Light, pose: Pose, texels: int) -> np.ndarray:
    """(3T, 3T, 3) BGR 0..1 picture of face f, row by row as read in the standard view, lit in 3D."""
    n = 3 * texels
    coord = (np.arange(n) + 0.5) / texels  # texel centers in cubie units
    u, v = np.meshgrid(coord, coord)  # u: right along a row, v: down a column
    col, row = np.minimum(u.astype(int), 2), np.minimum(v.astype(int), 2)
    lx, ly = u - col - 0.5, v - row - 0.5  # position inside the cell, -0.5..0.5

    # Signed distance to the rounded tile outline (negative inside); its gradient points outward.
    half = 0.5 - look.gap
    radius = min(look.radius, half)
    qx, qy = np.abs(lx) - (half - radius), np.abs(ly) - (half - radius)
    sdf = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - radius
    cover = np.clip(0.5 - sdf * texels, 0, 1)  # 1 on the tile, 0 in the groove, one-texel soft edge
    gy, gx = np.gradient(sdf)
    norm = np.hypot(gx, gy) + 1e-12
    tilt = look.bevel_angle * np.clip(1 + sdf / look.bevel, 0, 1)  # 0 deep inside, full at the rim

    origin, right, down, normal = FACE_FRAMES[f]
    outward = (gx / norm)[..., None] * right + (gy / norm)[..., None] * down
    normals = np.cos(tilt)[..., None] * normal + np.sin(tilt)[..., None] * outward
    p_cam = pose.apply(face_point(f, u, v))
    n_cam = normals @ pose.R.T
    to_light = light.position - p_cam
    to_light /= np.linalg.norm(to_light, axis=-1, keepdims=True)
    to_eye = -p_cam / np.linalg.norm(p_cam, axis=-1, keepdims=True)
    halfway = to_light + to_eye
    halfway /= np.linalg.norm(halfway, axis=-1, keepdims=True)
    diffuse = np.clip((n_cam * to_light).sum(-1), 0, None)
    specular = np.clip((n_cam * halfway).sum(-1), 0, None) ** look.shininess

    tile_colors = np.array([look.colors[facelets[9 * f + i]] for i in range(9)], float)
    albedo = tile_colors[row * 3 + col]
    if FACES[f] == "U" and look.logo:
        mask = np.zeros((n, n), np.uint8)
        for line in look.logo:
            pts = np.round((texels * (1 + np.asarray(line, float)) - 0.5) * 16).astype(np.int32)
            cv2.polylines(mask, [pts], False, 255, max(1, round(look.logo_width * texels)), cv2.LINE_AA, shift=4)
        a = (mask / 255.0)[..., None]
        albedo = albedo * (1 - a) + np.array(look.logo_color) * a
    seam = (1 - look.seam_black) * look.seam_dark * albedo + look.seam_black * np.array(look.body)
    albedo = cover[..., None] * albedo + (1 - cover[..., None]) * seam

    shade = (light.ambient + light.diffuse * diffuse) * (0.55 + 0.45 * cover)  # grooves get less light
    color = albedo * shade[..., None] + look.specular * (specular * (0.25 + 0.75 * cover))[..., None]
    return np.clip(color * np.array(light.color), 0, 1)


def to_supersampled(xy, ss: int) -> np.ndarray:
    """Pixel coordinates (pixel centers at integers) -> the same point in an image ss times larger."""
    return (np.asarray(xy, float) + 0.5) * ss - 0.5


def draw_cube(canvas: np.ndarray, facelets: str, cam: Camera, pose: Pose, look: Look, light: Light,
              ss: int = 1) -> np.ndarray:
    """Paint the cube into `canvas` (float BGR 0..1, ss times the camera size); returns its coverage (alpha)."""
    h, w = canvas.shape[:2]
    alpha_total = np.zeros((h, w), np.float32)
    for f in visible_faces(pose):
        corners = cam.project(pose.apply(face_point(f, [0, 3, 3, 0], [0, 0, 3, 3])))  # TL TR BR BL
        dst = to_supersampled(corners, ss).astype(np.float32)
        side = max(np.linalg.norm(dst[i] - dst[(i + 1) % 4]) for i in range(4))
        texels = int(np.clip(side / 3, 16, 112))
        tex = face_texture(facelets, f, look, light, pose, texels).astype(np.float32)
        m = 3 * texels - 0.5
        src = np.float32([[-0.5, -0.5], [m, -0.5], [m, m], [-0.5, m]])
        # Work only inside the face's bounding box: shift the homography so the box's corner is (0, 0).
        x0, y0 = (int(max(np.floor(dst[:, k].min()) - 2, 0)) for k in (0, 1))
        x1, y1 = int(min(np.ceil(dst[:, 0].max()) + 3, w)), int(min(np.ceil(dst[:, 1].max()) + 3, h))
        if x0 >= x1 or y0 >= y1:
            continue
        homography = cv2.getPerspectiveTransform(src, dst - np.float32([x0, y0]))
        size = (x1 - x0, y1 - y0)
        warped = cv2.warpPerspective(tex, homography, size, flags=cv2.INTER_LINEAR)
        alpha = cv2.warpPerspective(np.ones(tex.shape[:2], np.float32), homography, size, flags=cv2.INTER_LINEAR)
        region = canvas[y0:y1, x0:x1]
        region *= 1 - alpha[..., None]
        region += warped * alpha[..., None]
        alpha_total[y0:y1, x0:x1] = np.maximum(alpha_total[y0:y1, x0:x1], alpha)
    return alpha_total


def _polygon_area(pts) -> float:
    x, y = np.asarray(pts, float).T
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))  # > 0 when clockwise on screen


def _visible_fraction(quad, occluder, width, height) -> float:
    """Share of a quad's area that is inside the image and not covered by the occluder."""
    area = abs(_polygon_area(quad))
    if area < 1e-6:
        return 0.0
    x0, y0 = np.floor(quad.min(0)).astype(int)
    x1, y1 = np.ceil(quad.max(0)).astype(int) + 1
    x0c, y0c, x1c, y1c = max(x0, 0), max(y0, 0), min(x1, width), min(y1, height)
    if x0c >= x1c or y0c >= y1c:
        return 0.0
    mask = np.zeros((y1c - y0c, x1c - x0c), np.uint8)
    cv2.fillConvexPoly(mask, np.round((quad - [x0c, y0c]) * 16).astype(np.int32), 1, cv2.LINE_8, shift=4)
    seen = mask.astype(float)
    if occluder is not None:
        seen *= 1 - occluder[y0c:y1c, x0c:x1c]
    return float(np.clip(seen.sum() / area, 0, 1))


def frame_labels(facelets: str, cam: Camera, pose: Pose, occluder: np.ndarray | None = None) -> dict:
    """Everything the face geometry model (2.2) learns from, in image pixels.

    faces: each visible face with its outline (TL, TR, BR, BL as read in the standard view, so the
    face's rotation in the image is part of the label) and its nine tiles (cell quads, centers, color,
    facelet index, visible share). corners: the 8 cube corners, visible when one of their faces is.
    `occluder` (H, W, 0..1) marks pixels covered by fingers.
    """
    faces = []
    shown = visible_faces(pose)
    for f in shown:
        _, _, _, normal = FACE_FRAMES[f]
        center = pose.apply(face_point(f, 1.5, 1.5))
        facing = float(-np.dot(normal @ pose.R.T, center) / np.linalg.norm(center))  # 1 = straight on
        outline = cam.project(pose.apply(face_point(f, [0, 3, 3, 0], [0, 0, 3, 3])))
        tiles = []
        for i in range(9):
            r, c = divmod(i, 3)
            quad = cam.project(pose.apply(face_point(f, [c, c + 1, c + 1, c], [r, r, r + 1, r + 1])))
            mid = cam.project(pose.apply(face_point(f, c + 0.5, r + 0.5)))
            label = facelets[9 * f + i]
            tiles.append({"facelet": 9 * f + i, "name": f"{FACES[f]}{i + 1}", "label": label, "color": COLOR_OF[label],
                          "quad": quad.round(2).tolist(), "center": mid.round(2).tolist(),
                          "visible": round(_visible_fraction(quad, occluder, cam.width, cam.height), 3)})
        faces.append({"face": FACES[f], "color": COLOR_OF[FACES[f]], "facing": round(facing, 3),
                      "outline": outline.round(2).tolist(), "tiles": tiles})
    corners = []
    for name, sign in CORNERS.items():
        xy = cam.project(pose.apply(1.5 * np.array(sign, float)))
        in_frame = bool(0 <= xy[0] <= cam.width - 1 and 0 <= xy[1] <= cam.height - 1)
        covered = bool(in_frame and occluder is not None and occluder[int(round(xy[1])), int(round(xy[0]))] > 0.5)
        corners.append({"name": name, "xy": xy.round(2).tolist(), "in_frame": in_frame,
                        "visible": any(FACES.index(ch) in shown for ch in name), "occluded": covered})
    cx, cy = cam.center
    return {"width": cam.width, "height": cam.height, "camera": {"f": cam.f, "cx": cx, "cy": cy},
            "pose": {"R": pose.R.round(6).tolist(), "t": pose.t.round(4).tolist()}, "facelets": facelets,
            "scheme": STANDARD_SCHEME, "faces": faces, "corners": corners}
