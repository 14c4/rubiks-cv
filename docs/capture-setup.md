# Capture setup and operating envelope

The conditions under which the tracker is expected to work. Every claim of "it works" is a claim about this envelope. Widen it only after measuring.

Unrestricted speedcubing is a later target, not an initial promise.

## Hardware

- **Camera:** owner's phone through Iriun Webcam (virtual webcam, 640×480 via DirectShow). When the phone app is not connected Iriun serves a placeholder or black frames.
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

- **Mounting:** (fixed position? tripod, clamp, stack of books)
- **Distance from camera to cube:**
- **Angle:** (straight on, angled to see two or three faces)
- **Lighting:** (source, direction, color temperature; note any LED or fluorescent flicker)
- **Background:**

## Current operating envelope

| Condition | Supported | Evidence |
| --- | --- | --- |
| Turn speed | not yet measured | |
| Hands in frame | not yet measured | |
| Whole-cube rotations | not yet measured | |
| Lighting changes | not yet measured | |
