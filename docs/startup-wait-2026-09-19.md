# Remove the launcher's extra Wine-server wait

The launcher synchronized display scaling through a Proton `runinprefix` registry
helper, then started Lightroom through UMU's default `waitforexitandrun` verb.
That verb waits for the same prefix's Wine server to exit. The helper has already
started it, so Lightroom can wait for idle/background process shutdown before
it even begins rendering. This is separate from interactive frame pacing.

The custom Lightroom runner now defaults its application invocation to Proton
`run`. In the shipped Proton script, both `run` and `waitforexitandrun` initialize
the normal session; the latter additionally invokes `wineserver -w` before the
application. Helper commands still use `runinprefix`. The existing live-runtime
conflict guard still runs before scaling/theme helpers, and an explicit
`PROTON_VERB` in the launcher process environment remains respected. Other
runners retain their previous behavior.

## Actual launch measurements

Same copied signed-in prefix and diagnostic runtime, private Weston, 2× scaling,
MangoHud late limiter and retained photo. Each start was timed from immediately
before launching the CLI to the first committed loupe presentation timestamp.
This includes registry/theme synchronization and application loading; it is not
physical display latency. A settled screenshot then confirmed the library/photo.
No duplicate app was launched after an observation timeout.

| Launch | Mode | First photo submission |
|---|---|---:|
| A | Previous `waitforexitandrun` | 40.798 s |
| B | Explicit `run` | 12.839 s |
| A repeat | Previous `waitforexitandrun` | More than 100 s; eventually rendered |
| B repeat | Installed launcher default; no verb override | 13.640 s |

The A repeat exceeded the observer's 100-second deadline while its launch was
still alive. The existing process was inspected again and reached the signed-in
library; no exact total duration was retained, so only the lower bound is
reported. It was closed before the next launch. The first A's Quit also outlasted
a 15-second observation, and a subsequent process check confirmed its exit.
The other launches exited following Ctrl+Q within the longer observation window;
this series does not claim that every shutdown path is instantaneous.

The two `run` launches were approximately 27–28 seconds faster than the first
baseline. This supports removing the redundant wait; sample size, background
server lifetime, caches and host load limit generalization. It is not a claim
that Lightroom will always be ready in 13 seconds.

The installed launcher matches the source. All 28 unit tests pass, including
helper-vs-app verb selection, an explicit verb override and the existing runtime
conflict guard tests. The screenshots retain the signed-in library, and each
launcher reports 192 Wine DPI. Production Lightroom was neither restarted nor
replaced, and the desktop dispatch/workspace rules were not changed.

Numeric receipts: [measurements/20260919-startup-wait](measurements/20260919-startup-wait/).
The private trace format is documented in [photo presentation](photo-presentation-2026-09-19.md).
