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

Resource collection ran, but the attempted frame-time recordings did not produce
a valid recording covering the intended scored gestures. No speedup claim is
made from them. Remaining work includes reliable frame-time capture, real-application
resize validation, longer fallback/lifetime coverage,
and clean runtime packaging before promotion.
