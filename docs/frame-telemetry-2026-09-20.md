# Reliable pan recording and remaining timing limits

The frame recorder now produces sustained, validated photo-pan recordings. Warm
rendering in four controlled passes was centered on 8.33 ms per frame, consistent
with the configured 120 Hz limiter. One pass retained ten longer intervals up to
25.08 ms around recording controls. This is renderer timing in the headless
fixture, not proof of 120 distinct frames reaching the physical desktop display.

## Why the previous recording failed

Two independent problems were confirmed:

1. The advertised MangoHud socket was not serviced by the active photo-rendering
   instance. Perf samples showed MangoHud executing during panning. A bounded
   debugger probe then stopped in `overlay_QueuePresentKHR` on `vkd3d_queue` and
   read the active instance's control fd as **-1**, while `/proc/net/unix` showed
   a separate listening socket owned by the same process. A new connection to the
   already-full backlog returned EAGAIN. This explains why socket existence and
   successful command submission were insufficient to establish recording.
2. The isolated-input helper held Shift+F2 for 500 ms. MangoHud 0.8.4 checks keys
   every 100 ms and repeats a held toggle after 400 ms. A 500 ms press could start
   and stop recording. Sending the key only while an idle photo was displayed
   could also miss the rendered-frame key check.

The probe used the actual loaded MangoHud binary's disassembly and a breakpoint
at the control-fd test. It detached before timed runs. An earlier probe timed out
before the gesture and is not evidence for the active-instance result. The
successful probe's numeric readback and short stack excerpt are included below.

Upstream code places control processing and key polling in the frame snapshot,
before the `no_display` early return; hiding the overlay alone does not explain
the failure. See [MangoHud Vulkan presentation](https://github.com/flightlessmango/MangoHud/blob/v0.8.4/src/vulkan.cpp)
and [the key polling implementation](https://github.com/flightlessmango/MangoHud/blob/v0.8.4/src/keybinds.cpp).
This investigation did not patch MangoHud or establish which initial Vulkan
instance originally created the listening socket.

## Recorder fix and checks

`isolated-input.py record` now holds the hotkey for 200 ms.
`diagnostics/record-pan.py` starts a bounded ten-second vertical drag, sends the
start hotkey after one second, then stops logging five seconds later while the
photo is still moving. The helper verifies the owned headless X server before
input. No desktop input is injected.

The recorder requires a newly created output directory and independently verified
100% photo view with room to pan. It copies each original CSV without overwriting
other recordings, retains the phases, and rejects multiple/missing logs, stale
timestamps, short accidental bursts, malformed intervals and hotkeys outside the
gesture. It never treats a 400 ms recording as a successful five-second test.
All intervals, including long stalls, remain in its primary summary. The full
test suite passes 45 tests, including stale-log and double-toggle rejection and
retention of a synthetic 120 ms interior stall.

## Four controlled passes

The ordinary immutable rc1 private process remained signed in at 2× scaling.
There was no debugger, perf sampler, screenshot capture or resource recorder
during these runs. Main-thread hint minimum alternated 0/1024/0/1024; reset-on-fork
and all eight available CPUs remained unchanged. Minimum 1024 was restored after
the sequence. The desktop process was not changed during these tests.

| Pass | UI hint | Samples | Median | p99 | Maximum | Intervals >16.67 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A1 | 0 | 632 | 8.333 ms | 8.553 ms | 11.352 ms | 0 |
| B1 | 1024 | 617 | 8.332 ms | 8.552 ms | 8.932 ms | 0 |
| A2 | 0 | 626 | 8.333 ms | 8.541 ms | 12.337 ms | 0 |
| B2 | 1024 | 633 | 8.336 ms | 18.271 ms | 25.080 ms | 10 |

All 2,508 samples are retained. No interval exceeded 33.33 ms. The ten longer B2
intervals occurred at elapsed 0.052–0.303 seconds and 5.308 seconds, adjacent to
the recording hotkeys. This is consistent with control-related disturbance, but
does not prove causation or justify deleting those samples.

A separately labeled, fixed half-second exclusion at both recording boundaries
leaves 511/496/505/516 samples, with maximums 8.571/8.606/8.605/9.353 ms and no
intervals above 16.67 ms. This secondary view was added after inspecting the
control-adjacent stalls; it is not a replacement for the full measurements.
These passes support stable warm pan cadence, not a claim that the UI hint speeds
up rendering. Its measured improvement remains the earlier keyboard-menu result.

## Resource use during a separate pan

A separate 10.16-second resource pass used start/end snapshots, outside the timed
recordings. Lightroom used 27.6% of one CPU core; its Wine server used 3.0%.
Including the remaining prefix services, the total was 32.7% of one core, not
32.7% of the eight-core system.
Lightroom PSS was 1,896.6 MiB (about 1.85 GiB). One active GPU client's render
engine counter measured 58.4% busy over its counter interval. This gesture uses
both CPU and GPU; the CPU average does not rule out brief main-thread stalls.

The reported 3,878.8 MiB GPU-resident allocation figure can overlap CPU memory and
other clients. It is not dedicated VRAM usage and must not be added to PSS.
Full per-process values and separate engine counters are retained in the data.

[Measurements and the active-renderer probe](measurements/20260920-frame-telemetry/)
contain no photo pixels or credentials. Longer menu/photo transition outliers and
physical-display presentation remain separate questions. The working UI hint,
retained-photo fix, scaling and silent workspace-10 launch policy remain enabled.
