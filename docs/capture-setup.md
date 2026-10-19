# Capture setup and operating envelope

The conditions under which the tracker is expected to work. Every claim of "it works" is a claim about this envelope. Widen it only after measuring.

Unrestricted speedcubing is a later target, not an initial promise.

## Hardware

- **Camera:** owner's phone through Iriun Webcam (virtual webcam, 640×480 via DirectShow). When the phone app is not connected Iriun serves a placeholder or black frames. The image is **not mirrored** (owner's paper-text test, 2026-10-18; also the inspection clip's faces match a legal cube only unmirrored). The phone's own preview may look mirrored; trust the recorded frames.
- **OS and OpenCV backend:** Windows 11, OpenCV 5.0.0. Camera index 0 opens on both DirectShow and MSMF at 640×480 by default. DSHOW reports FPS as -1 (unknown) and measured ~22.7 fps; MSMF reports 29.97 and measured ~29.7 fps (3 s headless probe, 2026-10-13).
- **Cube:** stickerless 3×3 with a printed logo on the white center (D-003).
- **Color scheme:** standard (D-004), confirmed by the owner 2026-10-18: white opposite yellow, red opposite orange, green opposite blue; with white up and green in front, red is on the right. Face labels: U white, F green, R red, D yellow, L orange, B blue.

## Camera settings

Fill in after Milestone 0.4. "Honored" means the value read back after setting matched.

| Setting | Requested | Honored? | How it was set |
| --- | --- | --- | --- |
| Resolution | | | |
| Frame rate | | | |
| Auto exposure off | | | |
| Exposure value | | | |
| Auto white balance off | | | |
| White balance value | | | |
| Autofocus off | | | |

## Physical setup

Decided by the owner 2026-10-18: the camera faces the owner, who holds the cube up and turns it around in front of it (speedcubing-style inspection, then the solve). Synthetic training data (roadmap 2.1) is centered on this setup and varied from there.

- **Mounting:** camera fixed, facing the person (phone or webcam at roughly face height)
- **Distance from camera to cube:** arm's length or less (not yet measured)
- **Angle:** cube held freely; 1-3 faces toward the camera at a time
- **Hands:** fingers on the cube's sides and bottom, often covering edge tiles
- **Lighting:** room light (not yet recorded)
- **Background:** the person (face, shirt) and the room behind them

## Current operating envelope

| Condition | Supported | Evidence |
| --- | --- | --- |
| Turn speed | not yet measured | |
| Hands in frame | not yet measured | |
| Whole-cube rotations | not yet measured | |
| Lighting changes | not yet measured | |
