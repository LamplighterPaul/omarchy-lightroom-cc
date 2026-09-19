# Reproducible performance loop

Close Lightroom normally before choosing an overlay launch:

```sh
lightroom-omarchy-proton stage-mangohud
lightroom-omarchy-proton run-perf
```

The overlay is local to this app. Normal `run` does not enable it. With no
MangoHud installation, performance mode falls back to DXVK's FPS/frame-time HUD.
No Steam client, game purchase, RTSS injection or global overlay is required.
MangoHud can itself add overhead; compare an identical pass with it disabled.

Use one already-downloaded photo, a fixed window size, 2x display scaling and
100% photo zoom. Warm the photo once. Record 10 seconds idle, 20 seconds of
continuous left/right panning, then 10 seconds idle. Repeat three times without
changing image or zoom. Separately test opening/closing the same menu.
Do not count unchanged idle content as slow rendering.

Press Shift+F2 with Lightroom focused to record MangoHud CSVs (60-second limit).
In a terminal, `lightroom-omarchy-proton measure 40` records the prefix's CPU,
proportional memory and GPU engine counters once per second. It never switches
workspaces or moves the pointer. Results are under
`~/.local/share/omarchy-lightroom-cc/measurements/`.
Each resource sample reports whether a prefix window was focused. A background
run is not evidence of actual panning. GPU counters are per-client/engine;
unsupported counters are absent, never fabricated as zero utilization.

Compare frame-time p50/p95/p99, time above 16.67 ms and 8.33 ms, and the longest
stall during the active interval. Presentation cadence does not prove that the
photo pixels changed or that colours are correct. `diagnostics/frame-sample.py`
is an optional, heavier 20 Hz X11 brightness probe for the darkening symptom;
it is not an FPS meter and assumes the documented 2x window size. It records
numeric samples and hashes, not images. Measure capture overhead separately.

Change one variable per candidate; preserve the installed runtime and prefix
before promotion. Repeat the same interaction, confirm cloud/authentication,
scaling, theme and clean restart, then compare with the baseline. Rendering,
colour conversion, synchronization and CPU-side photo work are candidate causes;
none is established by an average CPU sample.

References: [MangoHud](https://github.com/flightlessmango/MangoHud) and
[DXVK HUD](https://github.com/doitsujin/dxvk#hud).
