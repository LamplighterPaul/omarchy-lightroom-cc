# Zoom transitions and remaining photo-loading delays

The performance profile sets Lightroom's existing `animationSpeed` preference
to zero before launch. Controlled restart comparisons reduced median time to a
settled zoom image by about 53–55%. This removes the animation, not rendering or
decoding work. It does not establish higher FPS or native performance parity.

## Restart comparison

The isolated Weston fixture used the pinned 11.7-3-rc1 runtime, performance
profile, UI scheduling hint, 2x scaling and the same mountain-lake photo. Each
run alternated Fit/100% eight times with Space, 1.5 seconds apart. Each condition
started a fresh Lightroom process. The last run used the changed launcher to
apply the preference. The experiment order was off, original, off.

| Animation | Median first changed image | Median settled image | Settled range |
| --- | ---: | ---: | ---: |
| Off, first run | 162.48 ms | 162.48 ms | 141.07–178.30 ms |
| Original (`1`), restart | 110.24 ms | 342.70 ms | 318.64–366.49 ms |
| Off, launcher repeat | 154.86 ms | 154.86 ms | 138.82–174.90 ms |

The original animation starts changing earlier, then spends about another
quarter-second moving toward the final view. With animation off, the captured
region changes directly to its final view. No blank-region samples occurred in
these 24 zoom transitions; this is not a guarantee against every flicker.

Capture ran at 20 Hz with GPU readback and PNG output. These numbers include
observer overhead and up to roughly one sample interval of detection delay.
They are not unobserved input latency or physical-display measurements.
`diagnostics/transition-latency.py` measures a central 160×160 region in the
720×450 captured image, using capture-completion monotonic timestamps. It
requires stable baseline/final samples and a distinct final image; frozen,
blank or unstable regions are not scored as success. First change uses mean
absolute RGB difference >5; settling requires all remaining samples <2 from
the final region. A different crop can produce different timing.

Numeric evidence is in [measurements/20260920-transitions](measurements/20260920-transitions).
Private photos and full application preferences are not published.

## Remaining delays

Eight next/previous-photo transitions after the second off run still took a
median 540 ms to settle. One took 1.42 seconds, including a late image update;
another took 799 ms. The other six were 482–547 ms. There were no blank-region
samples. This single photo pair is not a controlled animation comparison and
does not establish improvement or regression in photo loading. Loading and
remaining menu outliers still need separate attribution.

Two subsequent keyboard-menu smoke tests completed all 24 openings each. Median
input-to-X11-map times were 54.93 ms and 47.60 ms, but their maxima were 1.158 s
and 647 ms. Five and two openings respectively exceeded 150 ms; these are kept
in the numeric evidence. Each test resets navigation and re-enters photo view,
so it does not isolate steady-state menus from view preparation or startup
work. The private Weston display received SIGTERM after the transition captures
and was restarted before these menu tests; the desktop process was unaffected.
There is no animation-on menu control here, so no menu-speed claim follows.

The actual GPU preferences screen reports automatic full acceleration. The
custom-mode checkbox values in the preferences file do not establish which
features Auto mode enables. No GPU-processing setting was changed.

## Reversal and safeguards

The launcher saves only the original numeric animation value in a local
`animation-profile.json` beside the prefix, then atomically replaces that one
preference. It skips edits while Lightroom is running in the selected prefix,
and skips ambiguous/missing preferences or invalid backup data. Credentials,
photo edits and GPU-processing preferences are preserved.

Close Lightroom normally before changing modes:

```sh
LRCC_ANIMATIONS=original lightroom-omarchy-proton run
```

The performance profile defaults to `off`; other profiles default to `original`.
The environment override applies to that launch only. An externally changed
nonzero preference is preserved during restoration. Unit tests cover exact
restoration, preservation of other settings, live-prefix refusal, ambiguous
keys, external changes and the transition scorer's rejection cases.
