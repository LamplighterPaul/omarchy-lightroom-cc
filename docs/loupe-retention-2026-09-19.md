# Photo background repaint: isolated candidate

A targeted X11 candidate now preserves the photo during the reproduced drag.
It is **not the production runtime** and is not yet a general stability or
60/120 FPS result. Production Lightroom remained on 11.7-2 throughout these tests.
The [candidate patch and diagnostic source](https://github.com/LamplighterPaul/lightroom-omarchy-proton/commit/6ac4f2d)
are published separately from the active runtime manifest.

## Observed overwrite

A private diagnostic read a destination pixel immediately before and after
Wine's `X11DRV_PatBlt`. During the scored ten-second drag, 775 of 777 paired
observations changed image content to the flat `0x1c1c1c` background. There were
no interleaved diagnostic rows within those pairs. A later combined probe saw
GPU copies restore image pixels between these fills.

A debugger stop in the isolated process identified this call path:

```
X11DRV_PatBlt
NtGdiPatBlt(... width=2732, height=1151, rop=PATCOPY)
call_window_proc(hwnd=0x40db2, msg=15 /* WM_PAINT */)
update_now / NtUserRedrawWindow
```

The window's class was `loupeView`, with the same 2732×1151 client extent.
This is a fill from Lightroom's paint handler, not the default
`WM_ERASEBKGND` handler. The full debugger output remains private.

The first pixel-read probe masked flicker (0/280 blank samples); reads before
only, after only, and an XSync-only variant still produced 21, 12 and 60 blank
samples respectively. An uninstrumented control produced 94. Adding PatBlt
reads could worsen flicker (91, or 153 with both probe families). Therefore no
readback or extra synchronization was promoted as a fix.

## Candidate behavior and measurements

The opt-in `LIGHTROOM_OMARCHY_RETAIN_LOUPE=1` candidate suppresses the full-client
PATCOPY that would cover an already presented native photo surface. It does
not inspect colors or add GPU waits. Tracking is removed on detach/destruction;
the native surface must still have active references and presentation ownership.

The initial implementation performed a window lookup at the fill. Same binary,
photo, 2× scale, private output and MangoHud 120 Hz limiter:

| Candidate option | Blank samples / captured samples |
| --- | ---: |
| Enabled | 0 / 280 |
| Disabled | 112 / 280 |
| Enabled again | 0 / 280 |

A refinement cached destination information outside the GDI drawing path and
also produced 0/280. The latest source additionally caches the DCE's owning
HWND when assigned, then matches HWND, drawable, origin and full extent. This
avoids both a window-manager lookup under the DC lock and matching another
window merely because it occupies the same rectangle. This final revision
also compiled without warnings and produced **0/280** blank samples in a new
isolated drag. Its central photo region changed across 99 distinct sampled
luminance values during the drag, providing evidence that the image continued
updating rather than simply retaining a frozen frame. All 24 launcher unit tests pass; those tests do not validate
native rendering or the new driver's lifetime behavior.

All these counts are **appearance evidence**, not FPS or exact blank duration:
Weston readback perturbs timing. A threshold of mean luminance <40 describes
this particular test photo only. Photographs stay private. Numeric observations
and input boundaries are in [measurements](measurements/20260919-loupe-retention/).

## Interaction and regression limits

The first grid/photo-change smoke test remained in menu-bar navigation and did
not exercise those actions. It is invalid as evidence for those views. The
input helper now sends the additional Escape needed to leave the menu bar.
Corrected screenshots visibly confirm a grid view and switching to another
photo. Resize checks and longer use still need comparison against the baseline.

The `loupe-background.c` probe now passes **21/21 compositor checks in both
baseline and retained modes**. It checks first presentation, full and partial
fills, unrelated and top-level windows, an overlapping sibling with identical
geometry, resize before and after a new presentation, renderer release, and a
recreated window without a renderer. These are bounded synthetic checks, not a
long-running application stability result.

The earlier fixture failure had multiple causes. A staging texture read confirmed
that the GPU rendered red, while the child window's `GetPixel` could still read
stale GDI storage. The runner now checks pixels from the private compositor.
The fixture's own AppDefaults selects `ClientSideGraphics=N` to exercise the
observed X11 PatBlt path rather than a cached parent DIB. A diagnostic GDI read
flushes the synthetic fill before capture, and the helper keeps pumping messages
while waiting for capture acknowledgement. GPU staging reads and GDI synchronization
exist only in this probe; the candidate driver adds neither. The numeric results
are [baseline](measurements/20260919-loupe-retention/regression-baseline.json) and
[retained](measurements/20260919-loupe-retention/regression-retained.json).

## Warm presentation timing and power

The earlier hotkey/control recording attempts failed to cover the intended
phases. A separate configuration using MangoHud's documented
[`autostart_log=1` and `log_duration=180`](https://github.com/flightlessmango/MangoHud/blob/master/data/MangoHud.conf)
now records from launch. All three runs below used the same candidate binary,
2× scaling, private 120 Hz output, MangoHud late 120 Hz limiter and DXVK cap off.
Only `LIGHTROOM_OMARCHY_RETAIN_LOUPE` changed. The signed-in copied profile showed
the same lake photo. No production input was sent.

The sequence was Escape twice, maximize, detail view, ten-second pan, five menu
cycles, resize smaller, maximize, then another ten-second pan. Screenshots were
taken after three-second settles at size changes and **after**, not during, the
pans. The second pan is scored below; the complete 45-second interaction sequence
also has resource samples. Settled real-application screenshots show matching
correct layout in baseline and retained modes, including after re-enlarging.

| Retention | Recorded intervals | Median ms | p95 ms | p99 ms | Max ms | Over 16.67 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Disabled | 653 | 12.462 | 14.968 | 18.634 | 26.420 | 10 |
| Enabled | 973 | 8.336 | 8.474 | 8.566 | 13.640 | 0 |
| Disabled again | 539 | 15.019 | 16.970 | 21.066 | 26.845 | 33 |

Filename timestamps have one-second precision, so each gesture boundary is
trimmed by one second. Every interval inside that span is included, including
stalls. Their summed frame durations match the approximately 8.1-second recorded
spans within one frame, unlike sparse/startup portions of these same logs that
contain new-context timing artifacts. Raw scored intervals and summaries are in
[the numeric evidence](measurements/20260919-loupe-retention/warm-pacing.json).
This is evidence of improved warm-drag **presentation pacing**, consistent with
the eliminated repaint. It is not an end-to-end input-latency measurement or
proof of sustained display FPS. MangoHud logs do not identify individual
swapchains; the sum check cannot establish surface identity by itself. Startup
warmup and host activity were not perfectly controlled, and there is one enabled
run in this timing series. Menu latency and long stalls remain open.

The refreshed live production audit showed all eight CPUs available, main nice 0,
no cgroup CPU/RAM quota and no cgroup throttling. The host was on AC with
performance platform profile, performance EPP, turbo enabled and maximum CPU
performance percentage 100. Intel's governor reported `powersave`; observed
clocks still reached 4.4 GHz. The graphics maximum was 2500 MHz, equal to RP0.
Configured package long/short power limits were 40/50 W. These are hardware
policy values, not measured watts; privileged energy counters were unavailable.
No host policy was changed.

During the first disabled interaction sequence, prefix CPU usage peaked at
384.52% (100% is one core), PSS at 2505.21 MiB and package temperature at 73°C.
Thermal-throttle counters did not increase. See the numeric summaries for the
other sequences; whole-sequence resource maxima must not be attributed solely
to the scored pan. The recorder now saves AC state, frequency ceilings, power
constraints and temperatures alongside CPU, memory, GPU-engine counters and
cgroup limits.

Remaining work includes repeated per-surface timing, remaining menu/application
stalls, longer fallback/lifetime coverage and clean runtime packaging before
promotion. Production still runs 11.7-2.

## Packaged 11.7-3-rc1

The [candidate recipe and packager](https://github.com/LamplighterPaul/lightroom-omarchy-proton/commit/dee31af)
assemble a fresh pinned GE archive with 14 checksum-verified components. It
includes the tested retention driver, deferred threadpool close and optional
menu timing. Existing colour compatibility code is unchanged. The shared
build's unrelated Direct2D experiment is excluded. Supplying the stable runtime
against this recipe correctly fails checksum validation without creating output.
All 14 hashes were checked again after assembly.

The [launcher selector](https://github.com/LamplighterPaul/omarchy-lightroom-cc/commit/555cde1)
keeps the stable runtime as default and supports `--runtime
lightroom-omarchy-proton-11.7-3-rc1`. It refuses a runtime switch when live Wine
mappings in the selected prefix point to another runtime. A read-only check
identified the 12 existing production processes; selecting their actual stable
runtime reported no conflict. The launcher has 27 passing unit tests. This is
an explicit candidate selection, not an update of the running production app.

Packaged-runtime checks on the copied prefix:

- Both baseline and retention modes pass all 21 compositor regression checks.
- Disposable credential protection/unprotection, firewall enumeration and UI
  Automation shutdown probes pass.
- The six threadpool cases pass 25 iterations each on both x64 and i386.
- Lightroom loads the existing signed-in library, retains 192-DPI scaling, and
  displays the selected photo. Resize, menus, zoom and pan are exercised.
- Quit via Ctrl+Q exits the actual Lightroom process in 1.75 seconds. A restart
  without stopping the prefix reopens the library without a sign-in prompt.
  Screenshots confirm zoom changes between fit and the enlarged photo. A second
  Quit exits in 1.25 seconds. These are bounded Quit-path checks; they do not
  resolve the earlier inconsistent WM_CLOSE behavior or prove long-session
  stability. The production process remained running throughout.

The packaged run's warmed pan records 767 intervals, median **10.512 ms**, p95
12.442 ms, p99 16.365 ms and maximum 26.153 ms. Seven intervals exceed 16.67 ms.
The sum/span consistency check still passes. This second enabled result is
slower than the earlier 8.336 ms trial, so sustained 120 Hz performance is not
established. Menu instrumentation was enabled in this packaged run; the first
series did not enable it. DXVK/vkd3d library hashes match the experimental
runtime. These results preserve the warm-pacing improvement as a promising
observation, not a guaranteed frame rate.

Five File-menu openings give the following phase medians/maxima (ms):

| Phase | Median | Max |
| --- | ---: | ---: |
| Lightroom initialization callback | 6.531 | 9.204 |
| Popup initialization callback | 0.251 | 0.395 |
| Create popup | 0.471 | 0.518 |
| Layout | 0.438 | 0.660 |
| Show window | 1.556 | 1.974 |
| Paint | 0.749 | 1.373 |

This sample does not reproduce a long menu-phase stall. It excludes input queue
latency and compositor display latency, and runs under private Weston rather
than the user's Hyprland session. It therefore does not explain away the
reported desktop lag. Further profiling should target those missing boundaries
and longer stalls, rather than assuming a CPU-priority increase is the fix.
Numeric results are in [the packaged validation artifacts](measurements/20260919-rc1/).
