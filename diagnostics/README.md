# Local diagnostics

`lightroom-ui.c` enumerates Lightroom's windows, reads only its WebView2 rendering
setting, and optionally clicks its native Sign In control. It does not read
browser URLs, password fields or account tokens. Compile with the development
MinGW toolchain into `$LRCC_DATA/tools/lightroom-ui.exe`; use the launcher's
`ui` or `ui click-sign-in` command. The environment reader assumes x86-64
Windows structure offsets and is a development diagnostic, not application code.

`browser-status` reports only known rendering flags for processes in this Wine
prefix. An empty list can mean the app has exited or the process namespace is
not visible. Do not infer successful flag propagation from it.

`capture-webview` uses Node's built-in WebSocket client to request DOM size
counts and screenshots from a temporarily enabled localhost WebView2 debugger.
It never logs complete navigation URLs, page text, cookies or browser storage.
Screenshots remain private local diagnostics under the data directory.

Rendering policies persist in the selected Wine prefix. Profiles containing
`diagnostic` expose localhost port 19223; `no-sandbox-test` and
`no-sandbox-diagnostic` disable Chromium sandboxing and are temporary development
tests. Stop the selected runner and apply `repair-webview-rendering software`
after these experiments to remove the debug port and restore sandboxing.

## Main-window hang

`ui responsiveness` sends `WM_NULL` with a two-second timeout. A timeout is
evidence that the window is not responding, not a diagnosis of the cause.
Wine may return immediately if it already considers the window hung.

`omarchy-lightroom-cc --runner staging native-debug` launches standalone Wine
as GDB's child, avoiding attach restrictions on systems with ptrace scope 1.
Run it in an interactive terminal; GDB must be installed. It passes Wine's
normal exception signals through and suppresses frame arguments by default.
Press Ctrl-C at the hang, then use `thread apply all bt` to inspect stacks.
Debugger output can still contain private paths or data; review before sharing.
This command does not currently support the full Proton runner.

## Thread-pool lifetime

`threadpool-lifetime.c` reproduces deferred `CloseThreadpool` behavior with bound
timer, wait and work objects. It also covers cancellation and an empty pool.
Run only in a disposable or isolated prefix: the baseline runtime deliberately
hits its assertion in the timer case. See
[the candidate report](../docs/threadpool-2026-09-19.md) for evidence and limits.

## Resource limits and power

`lightroom-omarchy-proton measure 30` records CPU/memory/DRM activity, power
policy, CPU clocks, Xe GPU clocks, thermal-throttle counters and the main
process's scheduler/affinity/cgroup limits. It is read-only. Ancestor cgroups
can cover other applications; their usage counters are not Lightroom usage.
Thermal counters are cumulative, so correlate **increments** with an interaction.

## Composited appearance capture

`build-composited-capture.sh` builds a read-only client for the staged Weston's
output-capture protocol. Start the isolated fixture with `--capture` to authorize
it. See [the flicker report](../docs/flicker-2026-09-19.md) for usage and measured
overhead limitations. Capture photos stay local; commit only numeric timings.

The real-input helper uses Lightroom Desktop's **Space** zoom shortcut. `Z`
sets a pick flag in this application and must not be used to test zoom.

## Experimental photo-retention probe

`loupe-background.c` and `run-loupe-background.py` check actual private-compositor
pixels for GPU/GDI painting, overlapping windows, resize, release and recreation.
Both baseline and retained modes pass 21 checks; see [the candidate report](../docs/loupe-retention-2026-09-19.md).
Build with MinGW and `-ld3d11 -ldxgi -ldxguid -lgdi32 -luser32`, writing
`$LRCC_DATA/tools/loupe-background.exe`. The runner needs ImageMagick and the staged
`composited-capture` binary. Start the private Weston with `--capture` first.
Run on `DISPLAY=:1` and `WAYLAND_DISPLAY=lightroom-test` with `--expect baseline`
or `--expect retained`. It validates the private display and sends no desktop
input. Its isolated AppDefaults selects direct X11 graphics for this executable
only. Results and synthetic captures stay in `measurements/loupe-regression/`.
The test deliberately synchronizes and waits for captures: it measures painting
correctness, not performance.

The resource recorder also includes CPU policy ceilings, AC connection, RAPL
power constraints and CPU temperatures. Power constraints are configured limits,
not measured watts; unavailable privileged energy counters are not guessed.


## Private menu mapping timestamps

Build `x11-menu-events.c` with `cc -O2 -Wall ... -lX11` and run it for 1–60 seconds
on `DISPLAY=:1 WAYLAND_DISPLAY=lightroom-test`. It observes root `MapNotify`
events for Lightroom override-redirect windows without redirecting input or
reading pixels. Use `isolated-input.py menu-open` followed by two `escape`
actions; its JSON now includes monotonic input boundaries. Join those with the
observer's monotonic timestamps. Mapping is not proof of visible output; see
[the compositor investigation](../docs/menu-compositor-2026-09-19.md). The input
helper still validates private-compositor ownership before sending events.
