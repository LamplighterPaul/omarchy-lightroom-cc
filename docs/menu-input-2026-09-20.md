# Locate keyboard-menu delay before message polling

The prior mouse/keyboard comparison showed that warm Alt+F/Alt+E openings were
slower than mouse clicks for both menus. This follow-up uses the same private
signed-in, 2× fixture and leaves the desktop performance runtime unchanged.

Existing Wine key tracing first showed 26–50 ms between posting WM_SYSCHAR and
entering menu tracking. A small diagnostic-only win32u patch then marked posting,
PeekMessage entry, driver-event completion, queue retrieval, dispatch and default
menu handling. It adds no message reordering or changes to the application.

Six sequential keyboard openings produced these within-log intervals:

| Opening | Posted character → next poll entry | Poll entry → dispatch |
| --- | ---: | ---: |
| File 1 | 24 ms | <1 ms resolution |
| Edit 1 | 24 ms | <1 ms resolution |
| File 2 | 41 ms | <1 ms resolution |
| Edit 2 | 42 ms | <1 ms resolution |
| File 3 | 49 ms | <1 ms resolution |
| Edit 3 | 31 ms | <1 ms resolution |

The latter events share a millisecond timestamp, rather than proving zero cost.
The delay precedes Wine's polling call; the character is available immediately
when Lightroom asks for it. Default handling and menu tracking follow promptly.
This rules out slow queue retrieval as the explanation for this measured gap.
It does not identify every operation performed between the calls.

## Interrupted stack locations

Four successful diagnostic interruptions were armed at the posted-character
marker, with an external timer requesting a stop after 8–20 ms. They found the
main thread in Adobe AgKernel.dll twice, the Wine syscall dispatcher returning
through NtUserEnableMenuItem/MFC once, and vcruntime140 memmove once with an
AgKernel caller. This supports investigating application command-state refresh
and its runtime/API costs. It is not a statistically sampled CPU profile and
does not prove which function consumes most of the delay.

Adobe's private symbols are unavailable. GDB's nearest export labels and deeper
PE stack frames are not reliable enough to identify a particular Lua routine or
heap allocation. Earlier samples stopped on a Wine signal or after the menu was
already open; they are excluded. No debugger remains attached.

The first opening after each restart was much slower, including 1415 ms in the
final polling run. Only 24 ms of that opening lies between posting the character
and polling it. The preceding delay remains separate work. These first inputs
were not gated on an independently measured end of all startup work, so they
must not be treated as a pure cold-menu-rendering benchmark.

## Reproduction and scope

The [Proton diagnostic commit](https://github.com/LamplighterPaul/lightroom-omarchy-proton/commit/f612a78)
contains `omarchy/experimental/menu-input-timing.patch` and its usage notes. The final diagnostic runtime is
`lightroom-omarchy-proton-input-trace-v2`, copied from immutable rc1 with only
the rebuilt x64 Unix win32u component replaced. Its SHA-256 is
`0f0af7e91190a6acf35cc2b6406c8cf127e2f0ab7b6871cf7b62797933fa0b7f`.
The incremental SDK build succeeded; reverse-apply validation matches the
currently instrumented source. Actual keyboard openings and normal Quit were
exercised. This is diagnostic validation, not a production rendering regression
suite or a new performance fix.

Both trace and warning flags on the key channel are required: `+key`, rather
than just `trace+key`. One intermediate recording lacked the warning flag and
cannot support delivery-phase claims. Wine's log clock and host monotonic clock
are different; a bounded calibration sample is retained. The table above uses
only differences within the same Wine log.

The [numeric receipts](measurements/20260920-menu-input/) exclude full key logs,
photos and credentials. Full debugger records remain local. No CPU priority,
power limits, menu-state caching, or input-order workaround was applied: the
evidence does not yet justify changing those semantics.
