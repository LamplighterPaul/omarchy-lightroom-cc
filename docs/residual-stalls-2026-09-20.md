# Residual flash and menu latency investigation

After the real desktop recovered onto performance profile 11.7-3-rc1, Paul
reported that the black stutter was almost removed. He then closed Lightroom
normally and authorized further launches. This investigation uses the separate
signed-in prefix on the owned headless Weston fixture, at 2× and 120 Hz. The
runtime is the existing rc1-based presentation diagnostic build; no renderer
changes are promoted here.

## Appearance and photo submissions

The first exercise stayed at Fit and is excluded as a zoomed-drag test. After
correcting focus and visually confirming the enlarged photo, three separate
15-second recordings covered a vertical drag, eight zoom toggles, and six
alternating adjacent-photo changes. Each recording contains 300 compositor
captures at a requested 20 Hz. A central 160×160 region in the downsampled
image was checked for the reproduced RGB 28,28,28 background fill.

| Exercise | Samples >90% background | Distinct region means |
| --- | ---: | ---: |
| Enlarged photo drag | 0/300 | 98 |
| Zoom toggles | 0/300 | 37 |
| Adjacent-photo changes | 0/300 | 3 |

These captures do not reproduce the reported residual flash. Sampling can miss
short flashes, the region excludes the image edges, and readback perturbs
rendering. The result does not establish zero flicker on the desktop. The
changing drag samples and 976 successful photo submissions establish that the
drag did update the image rather than preserving a frozen frame.

The inner drag interval, trimmed one second at either end, contains 975
same-surface submission intervals: median 8.334 ms, p99 8.390 ms, maximum
8.434 ms, none above 16.67 ms. This recording includes compositor capture and
some offline image scoring activity, so it is not an unobserved performance
baseline. Submission timestamps are not physical presentation or input latency.

The compositor capture tool now also records the exact background-color fraction
and host monotonic timestamp. Dark photo content is kept separate from this
specific background color; neither alone proves a flash without inspecting the
image and interaction state. The rebuilt tool passed a live fixture capture.

## Menu delay follows the input method

An initial loop used mouse clicks for File and Alt+E for Edit. It also closed
menus after a fixed 230 ms delay. A slow File opening could then be incorrectly
matched to the subsequent Edit input. That loop is excluded from conclusions.

The new `diagnostics/menu-latency.py` waits for each MapNotify before closing
the popup and sending another opening. A timeout stops the sequence and retains
partial results; it does not quietly omit the stall or continue into ambiguous
matches. Each helper verifies ownership of the private X server before input.

The first serial opening after a restart took 1293 ms; this stall is retained
in the numeric receipt. Warmed blocks then compare like-for-like input in
mouse/keyboard/keyboard/mouse order, with ten openings per menu per block:

| Block | File median / max ms | Edit median / max ms |
| --- | ---: | ---: |
| Mouse | 10.892 / 11.598 | 11.112 / 16.585 |
| Keyboard | 56.201 / 97.498 | 52.503 / 69.146 |
| Keyboard repeat | 46.721 / 62.432 | 57.007 / 63.298 |
| Mouse repeat | 12.986 / 25.760 | 15.311 / 25.581 |

These are input-submission-to-X11-map receipt times, including observer
scheduling, on private Weston. They do not measure the desktop compositor's
visible pixels. The repeated difference follows the keyboard path for both
menus; it is not evidence that Edit rendering itself costs 50 ms. Existing
phase timers show short menu callbacks/layout/show/paint. The next target is
the delay before menu handling begins, including the first-opening stall.
Wine log timestamps and host monotonic timestamps must not be directly joined
without clock calibration.

Reproduce while the private fixture is running:

```sh
python diagnostics/menu-latency.py /tmp/lightroom-mouse.json --input mouse
python diagnostics/menu-latency.py /tmp/lightroom-keyboard.json --input keyboard
```

The observer is built from `diagnostics/x11-menu-events.c`; the input helper's
mouse coordinates target the current centered, 2× menu bar. Numeric receipts
are in [measurements/20260920-residual](measurements/20260920-residual/).
Photos and full application logs remain private. No CPU priority, power policy,
graphics runtime, authentication or desktop configuration changes were made.
