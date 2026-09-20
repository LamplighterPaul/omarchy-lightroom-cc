# Recover from a stale display controller query

Lightroom disappeared after the laptop resumed on 20 September. Its active
launcher log ends with an X11 protocol error: `BadRRCrtc`, request 140/20
(`RANDR / RRGetCrtcInfo`), resource `0x4b3`. There was no new systemd core dump
or Adobe minidump. The journal records resume at 09:14:11; inspection at 09:16
found the application gone. The X error itself has no timestamp, so the exact
trigger and exit time are not established. No kernel OOM kill was found in the
examined window, and 16 GiB of memory was available during inspection.

Wine's CRTC queries can use a screen-resources snapshot whose controller IDs
have since been retired. Xlib invokes its error handler before returning a
failed query. In rc1, Wine does not catch this particular error and delegates
to Xlib's default fatal handler. This mechanism was reproduced separately;
display reconfiguration during wake is the likely trigger for the reported
exit, rather than a demonstrated fault in the new zoom preference.

## Fix and build isolation

The rc2 Wine patch wraps all twelve CRTC-info queries with Wine's existing
expected-error mechanism. It accepts only `BadRRCrtc` for the RandR
`RRGetCrtcInfo` request and the exact requested resource ID. Callers then take
their existing NULL-result paths. Other protocol errors are not swallowed.
The request already waits for a reply, so no extra XSync round trip is added.

An isolated copy of the prepared source and build was used. The diagnostic
presentation patch was reversed there; rebuilding first reproduced rc1's
`winex11.so` hash exactly:

```
ede2fd9dbe769966907a475f49b45d5058c68cac9273ef69fc48b559343dbc58
```

Only the stale-CRTC patch was then added. The rebuilt rc2 component is:

```
206a83b3a7f7c338b7d1ab064a2de51c418ac893c18ce4b0018c4dd8fbb605fc
```

The other thirteen pinned components are unchanged. The shared diagnostic
build and the rc1 runtime were not overwritten. The source patch and candidate
recipe live in the Proton fork under `omarchy/patches/xrandr-stale-crtc.patch`
and `omarchy/candidates/11.7-3-rc2.json`.

## Fault-injection evidence

Testing used the owned private Weston display `:1`, never the user's display.
`diagnostics/randr-probe.c` waits twelve seconds, loads User32, creates a private
window, reports screen dimensions, and remains alive another twelve seconds.
Build it with the staged x86_64 MinGW compiler and run it through the selected
Proton runtime in the private prefix.

After the window initializes, attach GDB to that exact private process and load
the selected `winex11.so` symbols using its first mapped address as the `-o`
relocation. The resources are obtained by:

```gdb
set $resources = pXRRGetScreenResources(gdi_display,root_window)
```

On rc1, calling `pXRRGetCrtcInfo(gdi_display,$resources,0x7ffffffe)` reproduced
the same `BadRRCrtc` request 140/20 and exited the probe with code 1. On rc2,
calling `xrandr_get_crtc_info($resources,0x7ffffffe)` returned NULL; calling it
again with `$resources->crtcs[0]` returned valid information. The probe then
exited normally with code 0. Free valid CRTC results and screen resources, and
detach before doing interaction or timing tests.

Eight invalid/valid query pairs were also injected into the actual private
Lightroom process running rc2. Every invalid query returned NULL, every valid
query succeeded, and Lightroom survived. After GDB detached, twelve menu
openings, five zoom toggles, a ten-second vertical drag and next/previous photo
switches were exercised. This is crash-recovery validation, not a menu-latency
improvement claim. Remaining menu stalls are retained in the measurements.

The early attempt to use a pending breakpoint did not hit the target function
and is excluded from recovery evidence. The successful tests explicitly loaded
the relocated driver symbols and called the query path.

## Limits

This verifies recovery from the reported protocol error, including subsequent
valid queries. It does not prove that every suspend/resume sequence, output
change or crash is fixed. Physical suspend was not forced during this session.
There is no evidence here that photo files were deleted; preservation of the
very last unsaved edit cannot be determined from the available crash log.
