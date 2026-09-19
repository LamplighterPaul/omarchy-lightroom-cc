# Main UI scheduling hint

The performance launcher now gives Lightroom's main thread a utilization-clamp
minimum of 1024 on supported hybrid CPUs. Repeated keyboard-menu medians improved
from 65–66 ms to 46 ms without reducing any thread's available CPU set. The
reset-on-fork flag prevents newly created native workers inheriting the boost.
This replaces the affinity experiment as the selected scheduling approach.

Utilization clamping lets a task request a performance level; supported capacity
aware schedulers can use it for CPU placement. It is not a reservation of CPU
time, realtime priority or an affinity mask. See the [kernel documentation](https://www.kernel.org/doc/html/latest/scheduler/sched-util-clamp.html).
The machine's measured CPU capacities are 1024 on CPUs 0–3 and 676 on CPUs 4–7.
No governor, EPP, turbo, system clamp or platform power setting was changed.

## Controlled menu comparison

The normal immutable rc1 runtime ran in the private Weston fixture with 2× scaling
and the same signed-in photo. Four alternating blocks, 40 keyboard openings each,
used the existing serial input-to-X11-map recorder. No perf, debugger or pixel
capture ran during these blocks. Both conditions retained the reset-on-fork flag;
only the main thread's clamp minimum changed.

| Block | Minimum hint | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| A1 | 0 | 66.0 ms | 109.4 ms | 132.8 ms |
| B1 | 1024 | 45.8 ms | 132.1 ms | 157.5 ms |
| A2 | 0 | 64.5 ms | 107.8 ms | 311.6 ms |
| B2 | 1024 | 46.1 ms | 83.7 ms | 106.8 ms |

Median reductions were 30.6% and 28.5%. Long outliers remain, and p95 did not
consistently improve. MapNotify includes observer scheduling and precedes visible
display presentation. These measurements do not prove native parity or 120 FPS.

## Implementation and inheritance

`diagnostics/ui-scheduler.py` is a bounded, one-shot helper. It matches the current
user's Lightroom process using its name, exact resolved Wine prefix, mapped
Lightroom executable and selected Proton ntdll. It requires differing supported
CPU capacities within the thread's existing affinity mask. Existing custom
scheduling policy, nice values or clamp limits are preserved by skipping tuning.

It calls libc's `sched_getattr`/`sched_setattr`, preserves scheduling parameters,
requests the minimum and reset-on-fork, then checks readback. Unsupported systems
or failed optional tuning continue with normal launching. The helper exits after
applying or skipping; it does not continuously monitor the application.

An actual probe found that this machine's `uclampset -R -m 1024 -p PID` did not
set the reset flag: both parent and a new native thread retained minimum 1024.
Readback showed flags=0. A direct request without KEEP_POLICY sets the reset
flag successfully. The implementation uses KEEP_PARAMS to preserve nice/priority
and slice while allowing reset-on-fork to change. The regression test runs in a
disposable process and verifies that a new native thread has minimum 0, maximum
1024, no reset flag and the same CPU affinity.

After the controlled experiment, all 132 private threads had minimum 0 and access
to all eight CPUs. A normal Ctrl+Q and fresh launch through the new launcher
preserved authentication, the library, the same photo and 2× scaling. Readback
found only the main thread boosted; all 140 workers had minimum 0 and all eight
CPUs available. Forty fresh-launch openings per method measured 45.2 ms median
for keyboard and 13.7 ms for mouse, with maximums of 208.6 and 149.8 ms retained.

## Photo interaction checks

At 100% zoom, the private fixture exercised vertical dragging, eight zoom toggles
and eight alternating adjacent-photo changes. Separate 20 Hz compositor captures
contained 260 samples per sequence. The central 160×160 region in each downscaled
720×450 frame never exceeded 90% exact RGB(28,28,28) background pixels: zero blank
samples in all three sequences. Distinct rounded region means were 115, 34 and 3,
respectively, confirming changing imagery rather than a frozen frame. Inspected
low-luminance frames showed real photo content. Afterward, only the main thread
was boosted; all 130 workers retained minimum 0 and all eight CPUs.

This checks a sampled region and can miss brief flashes. Readback itself perturbs
rendering and cannot establish frame pacing. A separate attempt to record MangoHud
pan timing produced no CSVs; its third connection blocked in `unix_wait_for_peer`.
The recording helper was interrupted and its finally block restored the UI hint.
That attempt supplies no usable comparative timing evidence. Use bounded socket
timeouts in the next recorder investigation. Lightroom itself remained responsive.

## Deployment and opt-out

`make check` passed 42 tests, including the native worker inheritance test,
process/prefix/runtime matching, profile scoping and optional-helper failure.
The installed performance launcher defaults to `LRCC_UI_BOOST=auto`; stable
launches default to off. The same verified helper was applied to the existing
desktop Lightroom process without restarting it or changing workspace. It stayed
on Super+0 (workspace 10), with all eight CPUs available and nice 0.

To compare normal scheduling, close Lightroom normally and launch:

```sh
LRCC_UI_BOOST=off lightroom-omarchy-proton run
```

The flag affects that launch; it does not undo tuning in an already running
process. `status` reports the requested mode, while the application log records
whether the helper actually applied it. No Proton runtime bytes were replaced.
Remaining work includes long menu/photo outliers, usable pan frame-time telemetry
and broader worker-heavy workload validation.

[Numeric evidence and thread audits](measurements/20260920-uclamp/) contain no
photo pixels or credentials. Captures remain in the private local measurements.
