# Progress

Newest entry first. Claude reads the top entry at the start of each session.

## Current status

- **Current milestone:** 0 (OpenCV spike), 0.1 done, 0.2 in progress
- **Next concrete step:** finish 0.2 in `spikes/` (owner-written). Explained so far: coordinates, `cv2.rectangle`, slicing a cell and averaging with `.mean(axis=(0, 1))`, sampling with a margin before drawing, printing on spacebar. Pick up by reviewing the owner's current spike code.

## Commands that work

None yet. Add commands here and in the README only after running them successfully.

## Log

### Entry template

```
### YYYY-MM-DD: <milestone and short title>
Completed substeps: 
Runnable behavior and evidence: 
Checks run and results (pass / fail / skipped counts): 
Supported conditions and known failures: 
Hardware checks still required: 
Next step: 
```

### 2026-10-13: Milestone 0.1, live webcam feed
Completed substeps: 0.1
Runnable behavior and evidence: owner wrote `spikes/webcam.py` (DirectShow, camera 0) and reports seeing live video that closes on `q`. Claude ran a separate headless probe of camera 0 (no window): both backends open at 640×480. DSHOW reports FPS as -1.0 (unknown) and measured ~22.7 fps over 3 s; MSMF reports 29.97 and measured ~29.7 fps.
Checks run and results: none (spike, exempt from tests)
Supported conditions and known failures: DSHOW does not report frame rate; measure it instead of trusting `CAP_PROP_FPS`.
Hardware checks still required: camera model not yet recorded; which settings each backend honors (0.4)
Next step: Milestone 0.2

### 2026-10-12: Project planning
Completed substeps: none (planning only)
Runnable behavior and evidence: none
Checks run and results: none
Supported conditions and known failures: n/a
Hardware checks still required: confirm which camera settings can be locked on your machine (0.4)
Next step: Milestone 0.1
