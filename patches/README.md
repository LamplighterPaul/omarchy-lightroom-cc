# Experimental Direct2D patch

The separate `shcore-monitor-scale.patch` implements the monitor scale API used
by Lightroom. It is a Wine-derived LGPL-2.1-or-later change, developed here against
Valve Wine commit `46b29104e3741fe23bf5e2547196a253aab88c89` and built for the local
component test against Wine 11.10. See `scripts/build-shcore.py` and the
[performance report](../docs/performance-2026-09-19.md). It does not change color handling.

Extracted from 6im0n/lightroom-classic-on-linux commit
`7df91da9301dfb31eb228abac76972a9081e3fd2`,
`resources/patches/wine/d2d1-lightroom.patch` (effect.c hunk only).
It modifies Wine 11.10, LGPL-2.1-or-later. Wine source and license:
https://github.com/wine-mirror/wine/tree/2cac6ccf33c0807f374dc96f5a20e35a2da86157

This registers the missing ColorManagement effect using the existing Crop
implementation. It is a pass-through, **not a color transform**. The upstream
comment that Lightroom never uses this at edit time is unverified here.
Do not assume color accuracy. This is an isolated startup experiment.

On this machine, unmodified Wine reports missing effect
`{1a28524c-fdd6-4aa4-ae8f-837eb8267b37}` and Lightroom shows a graphics
initialization error. No other third-party patches have been applied.

Attribution and license scope are recorded in [THIRD_PARTY.md](../THIRD_PARTY.md).
The upstream MIT notices and Wine LGPL text are preserved in `LICENSES/`.
