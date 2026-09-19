# Recover an unreachable desktop before starting Lightroom

Paul reported that `run` did not work after selecting the performance profile.
The selected runtime was correct and no older runtime remained in the prefix.
Lightroom PID 2503934 and both Explorer helpers were blocked in
`load_desktop_driver` waiting for a desktop-window message reply. A clean
prefix stop and relaunch reproduced the hang.

The host itself could not open X11 display `:0`. The `/tmp/.X11-unix/X0`
endpoint was missing, while `X0_` remained a live listener held by the current
Xwayland process. Restoring the non-overwriting `X0 -> X0_` link made
`XOpenDisplay` succeed. Stopping the failed startup and launching again produced
a mapped Lightroom window on workspace 10, PID 2519491, logical size 1416×846.
The running process mapped the immutable 11.7-3-rc1 X11 driver and retained the
photo workaround and hidden MangoHud late limiter at 120 Hz. This is launch
validation, not a new frame-rate measurement.

The missing endpoint had also occurred during earlier performance work. Its
cause remains unknown; the local tmpfiles policy cleans this directory after
one hour, but no deletion event was captured to attribute this occurrence.
No compositor restart or system cleanup-policy change was needed.

The launcher now checks the X11 connection before dispatching or touching the
prefix. It can restore this specific missing endpoint only when the alternate
is a socket owned by the current user and `/proc` proves that a matching live
Xwayland process holds its listening socket. Existing endpoints, including
broken symlinks, are never overwritten. The connection is checked again after
repair; otherwise the command fails with an actionable error before starting
Wine helpers.

Desktop dispatch now reports a launch *request* and records the inner launcher's
stdout/stderr in a timestamped log, including early configuration errors.
Accepting a compositor command is no longer described as a successful app start.

Validation: 36 unit tests passed, including the listener-identity check,
preservation of existing endpoints, and failure before dispatch/prefix work when
the display is unreachable. The installed preflight connected to the repaired
real desktop. Private backtrace and runtime/window receipts are retained under
`~/.local/share/omarchy-lightroom-cc/measurements/startup-recovery/`.
