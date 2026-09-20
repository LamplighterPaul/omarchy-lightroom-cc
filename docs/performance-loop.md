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
resident memory (RSS) and GPU engine counters once per second. It never switches
workspaces or moves the pointer. Results are under
`~/.local/share/omarchy-lightroom-cc/measurements/`.
Each resource sample reports whether a prefix window was focused. A background
run is not evidence of actual panning. GPU counters are per-client/engine;
unsupported counters are absent, never fabricated as zero utilization.
RSS is an inexpensive estimate and counts shared pages in each process. For
detailed proportional memory, invoke `diagnostics/monitor.py` with `--pss`;
that mode can perturb interactive frame timing. PSS is `null` when disabled.
The recorder includes its own CPU cost and collection durations; compare an
identical gesture without the recorder before attributing stalls to Lightroom.

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

## Isolated real-input fixture

Developer tools in `diagnostics/headless-session.py` stage checksum-pinned,
application-local Weston packages and start a separate headless 2880x1800,
120 Hz display using the real GPU. Confirm the renderer in its log; software
rendering is not a valid performance comparison. The fixture uses display `:1`
and socket `lightroom-test` and refuses to replace an occupied display.

Close the normal app and stop/wait for its Wine server before `clone`. Cloning
refuses a running source prefix and never overwrites an existing test prefix.
The copied prefix remains private; it contains the user's genuine signed-in data.

```sh
python3 diagnostics/headless-session.py stage
python3 diagnostics/headless-session.py clone
python3 diagnostics/headless-session.py start
```

In another terminal, launch the existing test copy:

```sh
DISPLAY=:1 WAYLAND_DISPLAY=lightroom-test LRCC_DISPATCHED=1 \
  LRCC_PREFIX="$HOME/.local/share/omarchy-lightroom-cc/experiments/performance-headless/prefix" \
  lightroom-omarchy-proton run-perf
```

`isolated-input.py` supports `maximize`, `loupe`, `zoom`, `pan`, `menu-open`,
`escape`, `menus`, `record`, and `close` (requests Ctrl+Q; verify exit). Set both display variables as above. It verifies
that the X display belongs to the dedicated headless Weston before sending any
input. `pan` holds a real button and moves back and forth for about ten seconds;
input timestamps are written to `measurements/isolated-input.jsonl`.
`escape` outside a menu can leave photo view, so confirm the screen state.
Captures of the parent window omit separate popup windows.

For a bounded frame-time recording, first confirm a settled photo at 100% zoom
with room to pan vertically and logging off. Then run:

```sh
DISPLAY=:1 WAYLAND_DISPLAY=lightroom-test python3 diagnostics/record-pan.py /path/to/new-output-directory
```

This logs roughly five seconds inside a ten-second drag. Hotkeys are held for
200 ms and sent while frames are being rendered. MangoHud 0.8.4 checks keys on
rendered frames and repeats a held toggle after 400 ms; the old 500 ms press could
toggle twice. The recorder rejects short bursts, stale files and recordings
outside the gesture. All frame intervals, including stalls, remain in its main
summary. A secondary fixed half-second boundary exclusion helps identify control
effects without replacing the full result.

Do not assume the MangoHud control socket belongs to the active renderer:
Lightroom creates multiple Vulkan instances. In the tested session, the instance
presenting the photo had control fd -1 while another held the advertised socket.
Any separate socket client must use a timeout and verify the protocol greeting.
See [the telemetry investigation](frame-telemetry-2026-09-20.md).

Store a custom MangoHud config under the application data directory and pass
its absolute path as `LRCC_HUD_CONFIG`; the runtime container's `/tmp` is private.
An automatic logging delay is useful for repeated runs. Keep the warm-up gesture
separate from measured continuous pans; do not count intentional idle pauses as
stutters. Match CSV timestamps to the input intervals, and trim boundaries for
the CSV filename's one-second timestamp precision. Preserve stalls inside the
remaining interval, including those exceeding 100 ms.

The fixture validates rendering work and interaction repeatability. It does not
prove identical end-to-end presentation or input latency under the live Hyprland
compositor. Repeat the winning change on the normal desktop.

## Current presentation profile

The custom runner defaults to `LRCC_PRESENTATION=fast`: sync interval zero and
a frame cap following the destination monitor's refresh rate. If the refresh
rate cannot be read, the cap is 60. This is read at launch; restart after moving
to a display with a different refresh rate. `LRCC_PRESENTATION=upstream` leaves
DXVK presentation settings unchanged, and explicit `DXVK_CONFIG` options win.
See [the measured results and limitations](pacing-2026-09-19.md).

The resource timeline also records platform power policy, CPU governor/energy
preference, available CPU policy clocks, turbo policy, and host CPU/memory/I/O
pressure. Missing interfaces are omitted. Policy clocks are sampled context,
not effective per-thread frequency or proof of throttling. This recorder never
changes priority, governor, turbo or the power profile. Its one-second sampling
cannot attribute an individual short stall; use a targeted trace for that.

## Short thread trace

While reproducing a stall, run `lightroom-omarchy-proton trace 20` alongside the
MangoHud frame-time recording. It samples the main Linux thread every ~50 ms,
plus process I/O counters, into a timestamped JSONL file. It does not capture
stacks, credentials, filenames or photos, and does not change system policy.
The source tool `diagnostics/stall-trace.py` also accepts repeatable `--tid`
options for identified render/worker threads, or an expensive `--all-threads`.

A local five-second idle validation measured ~1.6% of one CPU core for the
main-thread sampler, versus ~22% for all 129 threads. These are sampler overhead
measurements, not Lightroom improvements. Do not leave all-thread mode running
as an overlay. Each trace includes scan duration and sampler CPU cost.

Kernel scheduler statistics were disabled on the test host. In that state the
trace deliberately omits runnable-queue delay: stale nonzero counters cannot
prove zero contention. CPU runtime, sampled wait channel and I/O remain useful
context, but cannot independently identify a GPU stall or prove the main thread
caused a frame spike. Read the [kernel scheduler statistics documentation](https://www.kernel.org/doc/html/latest/scheduler/sched-stats.html).

With Intel's active P-state driver, `powersave` does not mean the CPU is fixed
at its lowest clock. Energy preference and turbo policy matter; see the
[Intel P-state documentation](https://www.kernel.org/doc/html/latest/admin-guide/pm/intel_pstate.html).

## Optional MangoHud limiter

A separate A/B/A run found tighter photo-pan cadence with MangoHud's late
limiter than with DXVK's internal cap. After closing Lightroom normally:

```sh
LRCC_LIMITER=mangohud lightroom-omarchy-proton run-perf
```

This requires the staged MangoHud layer, disables DXVK's cap, and sets MangoHud's
cap from the destination monitor. It works with normal `run` too, with the HUD
hidden. Explicit `DXVK_CONFIG` and `MANGOHUD_CONFIG` remain user overrides; do not
add a second limiter when making comparisons. `LRCC_PRESENTATION=upstream`
bypasses this presentation profile. The default remains `LRCC_LIMITER=dxvk`
pending broader live compositor, menu and colour/flicker validation.
See [the limiter comparison](limiters-2026-09-19.md).

## Per-photo submission trace

The [photo presentation investigation](photo-presentation-2026-09-19.md) adds an
opt-in driver trace and decoder for individual loupe surfaces. Use
`isolated-input.py pan-vertical` when horizontal movement is clamped; verify
that photo submissions and visible content actually change before scoring.

The [mixed-photo run](mixed-photo-2026-09-19.md) covers photo selection, zoom,
vertical pans and menus, including the remaining occasional submission stalls.
The launcher also [removes an unnecessary startup wait](startup-wait-2026-09-19.md)
between its configuration helpers and Lightroom.

[Recorder overhead measurements](observer-cost-2026-09-19.md) explain why RSS
is now the default and why scored gestures should also run without the recorder.
