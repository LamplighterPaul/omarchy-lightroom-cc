> Historical standalone-Wine baseline. The later [Proton migration report](proton-2026-09-19.md) supersedes runtime and authentication status below.

# Performance and display work, 2026-09-19

Paul reported severe slowness and dark flicker while moving photos, and clarified
that the interface must follow Omarchy's 2x desktop scaling. The installed desktop
entry still uses Wine Staging 11.17 and the original authenticated prefix.

## Installed changes

- Use the current Hyprland Lua dispatcher to launch Lightroom silently on workspace
  10 (Super+0). Persistent local rules also suppress later activation requests.
- Read the destination monitor scale at launch, accounting for Xwayland's own
  scaling setting. This machine needs 192 Wine DPI because `force_zero_scaling` is true.
- Implement Wine's `GetScaleFactorForMonitor` in a small, source-built `shcore.dll`.
  Lightroom imports this API, whose upstream implementation returns 100% unconditionally.
  The patch returns the effective monitor scale independently of caller awareness
  and restores the thread's awareness context. The 200% API probe passed in all
  three awareness modes. Lightroom's controls were visually checked at 2x.
- Replace DXVK 2.7.1 and GE11-6's D3D12 pair with the components in the checksum-pinned
  [GE-Proton11-7 release](https://github.com/GloriousEggroll/proton-ge-custom/releases/tag/GE-Proton11-7).
  DXVK identifies itself as `v3.1-19-g601930949d111ed0`.
- Select Custom GPU mode, with both display and image processing enabled.
  [Adobe documents these as distinct acceleration levels](https://helpx.adobe.com/lightroom/desktop/kb/lightroom-gpu-faq.html).
  Camera Raw GPU3/GPU4 initialization succeeds; AI masking still reports CPU fallback.
- Load the already-installed NTSync kernel driver. Verified 99 NTSync descriptors
  in the regular Lightroom process after restart. No GPU or CPU identity spoofing.
- Disable Proton's Xalia helper and routine Proton debug logging in comparison runs.

The scale patch is Wine-derived and LGPL-2.1-or-later. Build it with
`python3 scripts/build-shcore.py`. With Lightroom closed normally, apply the profile
with `omarchy-lightroom-cc --runner staging repair-performance`. This validates
the archive, DLL checksum and preference keys before changing the prefix, and
retains the first originals under `patches/performance-backups/<prefix-hash>/`.
The installed profile and component hashes are recorded there in `profile.json`.

`config/ntsync.conf` is the one-line boot configuration. Installing it at
`/etc/modules-load.d/omarchy-lightroom.conf` requires root authentication. Loading
the module with `modprobe` alone lasts only until reboot.

## Measurements and limits

The event benchmark runs two Windows threads through 20,000 event round trips,
five times. Both comparisons use the same Wine binary, prefix and Bubblewrap
device bindings. The baseline masks only `/dev/ntsync` with `/dev/null`. No
Lightroom prefix or global device node is altered for this benchmark.

| Event benchmark | Median |
| --- | ---: |
| Wine server synchronization | 544.528 ms |
| NTSync | 193.843 ms |

This operation was **2.81x faster**. It is not an end-to-end Lightroom speedup.
An earlier, less controlled direct-vs-container run gave 5.8x; use the controlled
result above. Raw results are in `docs/measurements/20260919-sync-*.txt`.

The final 10.11-second regular-prefix sample reported 8.6% of one CPU core,
2539.2 MiB PSS, 2720.6 MiB summed RSS, and 2587.6 MiB GPU resident allocations.
GPU allocations can overlap CPU memory and shared clients; do not add these
figures. Different photo/grid states produced substantially different memory
footprints, so the earlier 5515.7 MiB GPU observation does not establish a
controlled before/after saving. A settled test-copy grid sample used 4.35% CPU
and 1369.3 MiB PSS, but is not comparable to the regular-prefix photo view.

The regular Lightroom window responded to WM_NULL in 1 ms. This checks event-loop
responsiveness, not rendering latency. Final screenshot showed a sharp photo,
enabled editing controls and normal online search; current console had zero
missing-access-token or failed-token-refresh errors. All 17 launcher tests passed.

Synthetic background pan/key messages did not reliably exercise real interaction.
The pixel sampler reported unchanged frames in those attempts. **No panning FPS,
interaction speedup, flicker fix or sustained stability result is established.**
The next check must use actual pan/zoom input while collecting resource and pixel
samples. Color fidelity remains subject to the pre-existing experimental Direct2D
pass-through; this work does not validate that workaround.

## Full Proton comparison

### Subsequent user validation

Paul confirmed that display scaling works, but reported that photo flicker
continues and opening files and menus remains choppy. Treat the interactive
performance and flicker issues as unresolved, despite the synchronization
microbenchmark improvement. His supplied screenshot shows the light Windows
File/Edit menu strip above Lightroom's dark custom interface. He requested
assessment of matching that strip to the current Omarchy theme (Tokyo Night),
with centered menu entries and additional spacing, and reiterated his preference
for a maintained Proton-based runtime. Colours have a Wine system-colour path;
centering requires menu layout work and is not an existing Omarchy window rule.
No menu styling changes have been applied or verified.

Reinspection confirmed the desktop entry and running wineserver still use
Wine Staging 11.17. The local Proton source tree has an `omarchy` branch and an
upstream GE remote, with uncommitted Wine/patch changes; it has no published
fork remote or completed custom distribution. GE-Proton11-7 is still marked
latest by its upstream release page at this check.

GE11-7 was tested through UMU in a separate copied prefix. It reported offline
despite host HTTPS access. Lightroom logged `No access token available` and
`Unable to refresh tokens`. Proton changes the Windows username to `steamuser`;
that is a possible migration issue, not a proven cause of the lost authentication.
Paul then observed a crash. Adobe produced a crash tag with action
`clear_auto_stackers`, but no recent system core or OOM event was available.
Xalia logged exceptions and consumed CPU; these observations do not prove it
caused the Lightroom crash. The full Proton candidate is stopped and is not the
desktop default. Do not bypass Adobe sign-in to repair this migration.

A local source branch exists at `/home/paul/Development/omarchy-proton`, based on
GE11-7 commit `c191f35dcebbeccfacd3b4c6f6eea026e588c1c2`, with the monitor-scale patch.
It is not a published or fully built custom Proton distribution. Maintenance
automation was deferred when Paul prioritized performance.

## Diagnostics

`diagnostics/resources.py PREFIX --seconds 10` samples CPU, PSS/RSS and DRM
allocations without recording process command lines or tokens.
`diagnostics/frame-sample.py` samples one Lightroom X11 photo region without
switching focus; it is not an FPS benchmark and expects a sufficiently large window.
`diagnostics/display-probe.c` verifies scale APIs; `diagnostics/sync-bench.c`
measures synchronization only. Screenshots and Adobe authentication data stay local.

An unrelated launch blocker was repaired: the live Xwayland server's `X0` socket
path was absent, while its alternate listener `X0_` existed. A non-overwriting
`X0 -> X0_` symlink restored XOpenDisplay. The reason the original path disappeared
was not established; no desktop restart was needed.
