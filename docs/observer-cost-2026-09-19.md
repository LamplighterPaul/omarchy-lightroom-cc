# Reduce the performance recorder's own interference

A completed on/off/on comparison found extra photo-submission stalls while our
resource recorder was active. Same private Lightroom session, image, zoom,
retention patch, late 120 Hz limiter and vertical gesture. Three 10-second drags
per block were scored with one second trimmed at each boundary. No screenshots
ran during scored gestures. The per-photo driver trace remained enabled.

| Recorder mode | Intervals over 16.67 ms, across three drags | Worst interval |
|---|---:|---:|
| Original detailed recorder | 19 | 25.713 ms |
| No resource recorder | 0 | 12.539 ms |
| Original recorder repeated | 14 | 26.218 ms |
| GPU descriptor filtering, still PSS | 9 | 23.918 ms |
| GPU filtering and lightweight RSS | 1 | 21.920 ms |

The unmonitored medians were about 8.33 ms. The lightweight recorder's medians
were 8.96–9.00 ms, so it is **not zero-overhead monitoring**. Host conditions and
caches vary, and this does not explain every desktop stall. It does establish
that heavy diagnostic sampling cannot be treated as neutral when profiling.
The earlier mixed-photo run also had a recorder child active, although that
child did not leave a completed report. Its timing results therefore include
potential observer interference.

## Changes

The GPU reader previously opened every descriptor's `fdinfo`, including event
and synchronization descriptors. It now first selects device descriptors under
`/dev/dri/`. A live comparison read 763 vs 6 fdinfo files in the main process,
and found identical six DRM client IDs and counter-field sets. Enumeration is
fresh each sample; vanished/reused descriptors are still handled defensively.

Continuous monitoring now uses RSS from the process stat record. Detailed PSS
requires `monitor.py --pss`, because `smaps_rollup` walks process memory mappings
and can interfere with the measured app. RSS is an estimate and double-counts
shared pages across processes; it must not be presented as PSS. `pss_mib` is
null when disabled. The one-shot `resources.py` sampler retains detailed PSS.

The recorder also reports host-monotonic sample timestamps, snapshot and total
collection wall times, and its own CPU time (excluding helper subprocesses).
Each recorder ran through an independently tracked tool process, and all four
40-second recordings completed before analysis.

| Mode | Recorder CPU seconds / 40 s | Median collection ms |
|---|---:|---:|
| Original | 2.559 | 65.018 |
| Original repeat | 2.271 | 63.837 |
| GPU filtering with PSS | 2.297 | 73.917 |
| GPU filtering with RSS | 1.096 | 28.618 |

GPU filtering alone did not reduce total collection time in that full run;
removing the repeated detailed memory scan made the larger difference. A live
validation prohibited every `smaps_rollup` read in lightweight mode while
confirming nonzero RSS and GPU counters. Detailed mode still returned PSS.
All 28 launcher tests and Python syntax checks passed.

## Resource observations

Across these recordings the prefix used median 42–45% of one CPU core, with a
maximum of 56.28%. Detailed PSS peaked at 2775.34 MiB (about 2.71 GiB). The final
lightweight run reported peak RSS 2955.61 MiB; it is a different metric, not a
memory regression. No thermal-throttle counter increased; maximum sampled CPU
sensor temperature was 84°C across the blocks. The first block's active render
client showed median 48.38% and maximum 56.79% engine activity. These are
per-client/engine counters, not whole-GPU utilization or proof of spare capacity
at every frame. The sampled graphics clock reached its 2500 MHz configured and
hardware maximum. No power, priority, quota or scheduling policy was changed.

One-second samples describe context; they cannot causally attribute individual
20 ms stalls. Scheduler runqueue delay remains unavailable with schedstats off.

Numeric gesture traces, resource extracts, original report hashes and summary:
[measurements/20260919-observer-cost](measurements/20260919-observer-cost/).
The complete resource reports and profiler output remain local.
