# Mixed photo, zoom and menu validation

The per-photo timing build was exercised across three adjacent library photos,
with Space zoom toggles, vertical dragging and five File menu open/close cycles
per photo. This used the same copied signed-in prefix, 2× scale and private
120 Hz Weston fixture, with retention enabled and MangoHud's late limiter.
The three selections were restored afterwards. No editing commands were sent.

Settled compositor screenshots showed the selected rock/mountain photographs
and changed zoom views, including correct photo content after menus closed.
These are visual checks at selected points, not continuous flicker detection.
Screenshots remain private. No capture ran during scored drags. The selected
phase windows exclude one second at each boundary; no intervals inside them
were removed. All selected callbacks reported successful copy submission.

| Photo | Intervals | Median ms | p99 ms | Maximum ms | Over 16.67 ms |
|---|---:|---:|---:|---:|---:|
| 1 | 962 | 8.338 | 10.479 | 23.480 | 4 |
| 2 | 858 | 9.347 | 12.380 | 26.525 | 7 |
| 3 | 849 | 9.466 | 15.477 | 24.560 | 9 |

No selected interval exceeded 33.33 ms. The longest CPU-side presentation
callback was 0.173 ms. These are submission intervals, not physical display
FPS. Unlike the previous single-photo warm test, the broader workload still
shows occasional stalls. This is not a controlled cold-cache benchmark: library
cache state and image decoding were not reset between photos.

Across 15 menu openings, the initialization callback median was 7.888 ms,
maximum 10.043 ms. Other measured phases had maxima below 2.2 ms. These do not
include the complete input-to-display path and do not establish desktop menu
latency. The private app subsequently quit normally using Ctrl+Q.

A resource monitor child was started but did not leave a completed recording
when its parent test command ended. Therefore no new CPU, memory, thermal or
power conclusion is drawn from this run; previous completed audits remain the
only resource evidence. Future mixed-workload runners must await their monitor
before exiting, or run it through its own managed tool session.

Numeric artifacts: [measurements/20260919-mixed-photo](measurements/20260919-mixed-photo/).
Trace implementation and limits: [photo presentation](photo-presentation-2026-09-19.md).
