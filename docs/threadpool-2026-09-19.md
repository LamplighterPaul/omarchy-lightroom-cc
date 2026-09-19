# Deferred thread-pool close candidate

The existing `11.7-2` shutdown assertion is reproducible in Lightroom and a small
standalone program. In the application trace, Wine's **timer queue thread** calls
`tp_object_submit()` after the pool is marked shut down. It trips
`assert(!pool->shutdown)` after Adobe has logged “Lightroom Exited”. This is a
lifetime issue, separate from the unresolved photo flicker and menu lag.

Microsoft documents [CloseThreadpool](https://learn.microsoft.com/en-us/windows/win32/api/threadpoolapiset/nf-threadpoolapiset-closethreadpool)
as releasing the pool asynchronously after its outstanding objects are freed.
The experimental Proton patch records the close request and postpones worker
shutdown until the pool's object count reaches zero. It keeps the submission
assertion. It does not change scheduling priority or presentation.

## Regression evidence

`diagnostics/threadpool-lifetime.c` uses only documented Windows APIs and no
Adobe files. Compile with the pinned Steam Runtime SDK's MinGW compilers.
Invoke the executable as `CASE ITERATIONS` in the isolated test prefix.

| Case | Behavior | Candidate x64 repetitions | Candidate i386 repetitions |
|---|---|---:|---:|
| normal | Timer finishes before pool close | 10 | 5 |
| timer | Pool close precedes the timer firing | 20 | 5 |
| wait | Pool close precedes a bound wait becoming signaled | 50 | 5 |
| work | Work object exists before close; submitted afterwards | 50 | 5 |
| cancel | Close pool, cancel and drain its timer | 500 | 5 |
| empty | Release pool without bound objects | 1000 | 5 |

All candidate cases passed. On unmodified `11.7-2`, normal passed and timer
reproduced the assertion (exit 1). These tests exercise object lifetime; they do
not establish compatibility with every application or prove absence of leaks.
An initial attempt to compare handle counts was discarded: Wine stubs
`ProcessHandleCount` to zero, making that result meaningless.

The first candidate application exit attempt is **invalid evidence**: the
isolation guard terminated the fixture when Paul focused his real Lightroom.
The launcher returning zero therefore did not prove a graceful application exit.
A later controlled run reopened the candidate, exercised twenty menu opens,
then posted `WM_CLOSE` to the confirmed Lightroom window. Linux PID 1965335
exited within 6.1 seconds of the request; the focus guard did not fire and the
log contains no assertion. The candidate remains separate from the production
runtime while packaging and further interaction checks are completed.

Private source logs: `logs/20260919-threadpool-original-proton.log` and
`logs/20260919-201337-595934-lightroom.log` beneath the app data directory.
The experimental patch lives in the companion Proton source repository at
`omarchy/experimental/threadpool-deferred-close.patch`; it is not in the
production manifest.
