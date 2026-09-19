# Per-photo presentation timing

An opt-in X11 diagnostic now timestamps only child `loupeView` surfaces, so the
photo's cadence can be separated from Lightroom's filmstrip and other swapchains.
The diagnostic runtime is copied from immutable 11.7-3-rc1 and replaces only
`files/lib/wine/x86_64-unix/winex11.so` (SHA256
`0beca0f19113d30ff24e486e51f8f334e93650b46a3748997f6c76b645eb910b`).
The [source patch and format](https://github.com/LamplighterPaul/lightroom-omarchy-proton/blob/63937c2/omarchy/experimental/loupe-present-timing.md)
are separate from the candidate. All 14 original rc1 component hashes still match.

## Workload validity

Horizontal gestures in this session produced no photo callbacks inside the
scored interval. Switching to vertical panning produced continuous photo
submissions. The input helper now supports `pan-vertical`; a separate, unscored
30-frame capture had 30 distinct central photo crop luminances. This confirms
changing photo content during that gesture rather than assuming that submitted
input necessarily moves the image. The photo was the same cached lake scene.
The earlier horizontal tests are not retroactively invalidated: they had their
own appearance checks, but gesture validity must be checked each session.

No pixel capture ran during scored gestures. Each 10-second gesture excludes
one second at each boundary; all callback intervals within the selected window
are retained. Same private 2880×1800/120 Hz Weston, 2832×1692 client, 2× scaling,
retained-photo patch enabled, same runtime and prefix. Each launch had a warmup
gesture, then three scored vertical gestures. MangoHud is loaded in both modes;
only the limiter is switched, with DXVK's cap disabled for MangoHud late mode.
No CPU/GPU power or priority setting changed. The desktop Lightroom stayed open.

## Limiter comparison: MangoHud → DXVK → MangoHud

| Limiter / pass | Intervals | Median ms | p99 ms | Maximum ms | Over 16.67 ms |
|---|---:|---:|---:|---:|---:|
| MangoHud / 1 | 975 | 8.333 | 8.496 | 9.388 | 0 |
| MangoHud / 2 | 975 | 8.334 | 8.463 | 9.020 | 0 |
| MangoHud / 3 | 973 | 8.336 | 8.503 | 14.646 | 0 |
| DXVK / 1 | 610 | 13.240 | 15.648 | 17.859 | 1 |
| DXVK / 2 | 608 | 13.329 | 16.436 | 16.932 | 2 |
| DXVK / 3 | 546 | 14.001 | 24.953 | 27.343 | 98 |
| MangoHud repeat / 1 | 975 | 8.333 | 8.505 | 9.324 | 0 |
| MangoHud repeat / 2 | 975 | 8.333 | 8.488 | 8.549 | 0 |
| MangoHud repeat / 3 | 974 | 8.333 | 8.475 | 8.534 | 0 |

All selected submissions completed the copy path (outcome 7). The longest
callback across all nine scored passes was 0.491 ms. Both MangoHud blocks
returned to approximately 8.33 ms cadence; DXVK medians were 13–14 ms. This
supports limiter placement as a material source of pacing overhead in this
candidate workload, rather than CPU-side X11 copying. The late limiter remains
an explicit option pending normal-desktop and broader interaction validation.
No general native-parity or visible 120 FPS claim follows from these results.

## Interpretation and limits

The `callback` spans entry through X11 submission cleanup. `geometry`, `clip`,
`copy` and `flush` identify its CPU phases. The copy phase includes overlay-shape
handling and retained-surface bookkeeping. XFlush submits commands: these times
are **not GPU execution time or visible frame intervals**. Faster submission
also does not by itself establish lower input-to-display latency.

The trace appends fixed-size records to a shared mapping, with no per-frame
stdio, screenshot readback or additional GPU wait. Clock reads, atomic indexing,
and mapping page faults still impose overhead, which has not been independently
quantified. These are comparative instrumented measurements, not proof of zero
overhead. Each row includes surface, window, extent and completion status;
results are grouped by surface/extent, avoiding cross-window Mango ambiguity.

Decode an original private binary trace and one input phase with:

```sh
python3 diagnostics/present-trace.py /absolute/trace.PID.bin \
  --phase /absolute/gesture.json --trim 1 --csv /absolute/selected.csv
```

The reader rejects invalid headers and truncated mappings, ignores uncommitted
rows and reports capacity exhaustion. A focused check exercised committed vs
uncommitted records and truncation. The driver compiled without warnings;
Python syntax checks and all 27 launcher tests passed. Numeric extracts are
under [measurements/20260919-photo-present](measurements/20260919-photo-present/).
Photographs, account state and full application logs remain private.
