# Post-authentication hang investigation — 16 September 2026

Resumed the existing authenticated Wine Staging 11.17 environment with
`omarchy-lightroom-cc --runner staging native-debug`. The graphics stack was
unchanged. Lightroom and its Bezel window opened on the workspace reached with
Super+0 (Hyprland workspace 10); the active desktop remained elsewhere.

## Observations

- `ui responsiveness` again reported timeout/error 1460 before GDB interruption.
- Wine reported the main process heap critical section at `0x1400d0` blocked by
  Windows thread `0x230`. Reading its owner field confirmed `0x230`, with a
  recursion count of one.
- The owner mapped to GDB thread 58 / Linux thread 29662 in this run. Its native
  backtrace stopped in `NtWaitForSingleObject`.
- All native thread backtraces were captured. Native GDB unwinding did not show
  the Windows callers across Wine's syscall transition, so this alone did not
  explain the hang.
- Inspection of the owner's saved Windows stack found addresses in
  `WaitForSingleObjectEx`, `_Thrd_join`, `CRClient.dll`, Camera Raw and
  `UnhandledExceptionFilter`. Deeper stack slots contained Wine heap routines,
  `free`, `malloc` and `AdobeGrowthSDK.dll` addresses.
- A saved exception record contained access violation `0xc0000005` at
  `ntdll.dll+0x5e206`. The saved context agreed on the instruction address:
  `add 0x10(%r11),%r14`. The exception parameters identified a read and reported
  address `0xffffffffffffffff`.
- Windows thread `0x354` had stack addresses in heap allocation and thread
  initialization while waiting on a critical section. Wine's timeout output
  also identified it as waiting for the heap owned by `0x230`.

Thread IDs and absolute addresses are specific to this execution. The Windows
stack inspection was a scan for module/export addresses, **not a validated
unwind**: slots can contain stale addresses and data pointers, and nearest-export
labels do not establish the exact function. Native Mesa threads also inherited
the main thread's GS/TEB value; those duplicate Windows stack scans must not be
counted as independent Windows threads.

## Interpretation and next experiment

The evidence suggests the visible hang is secondary to an access violation
while a worker owns the process heap lock, followed by a wait in Adobe crash
handling. It does not establish what originally damaged the heap, prove that
AdobeGrowthSDK caused it, or prove which object the owner is waiting for.

Next, catch the original exception before crash handling, recover and unwind
the saved Windows context, and identify the heap operation and its caller.
Use the module-relative fault address as a starting point rather than trapping
every Wine SIGSEGV (many are handled normally). Matching Wine symbols or a
Windows-aware unwinder are needed. Inspect the allocation/free history in an
isolated copy if the first-fault context establishes heap corruption. Keep the
GPU stack unchanged until this failure is understood.

The authenticated backup remains private and unchanged. The diagnostic process,
GDB and the selected prefix's helpers were stopped after capture. No editing,
export or cloud-sync result was verified.

Private evidence under the local data directory's `logs/`:

- `20260916-hang-backtrace.txt`
- `20260916-windows-stack-scan.txt`
- `20260916-hang-exception.txt`

These raw files are not included in the repository.

## Verified workaround and restart result

Created an isolated copy of the authenticated snapshot, keeping runtimes and
graphics configuration unchanged. Launched with `WINEDLLOVERRIDES=AdobeGrowthSDK=`.
The UI responded to `WM_NULL`, cloud thumbnails and albums loaded, and full-size
photos opened. The library reached 397 photos. `/proc/<pid>/maps` confirmed that
AdobeGrowthSDK was not loaded. The operator independently confirmed the result.

The community [Lightroom CC guide](https://github.com/sander110419/lightroom-cc-on-linux/blob/main/GUIDE.md#61-disable-adobegrowthsdk-ccs-copy--lightrooms-copy)
also describes disabling the optional SDK, but for a missing API on Wine 11.8.
This experiment's observed failure was different; the guide is corroborating
workaround history, not proof of our root cause.

Added `repair-growth-sdk` to write an empty `AdobeGrowthSDK` value under
`HKCU\Software\Wine\AppDefaults\lightroom.exe\DllOverrides`. This is scoped to
Lightroom in the selected Wine prefix. Adobe binaries, sign-in and licensing
are unchanged.

After applying the registry setting, requested a normal window close and
observed launcher exit status 0. Stopped remaining Wine helpers, then relaunched
without `WINEDLLOVERRIDES`. The library/photo view returned without a login
prompt and the UI response was received in 0 ms. Thus the authenticated session
survived a complete process exit, using persisted state rather than a live helper.

Applied the same registry setting to the regular staging prefix and regenerated
its desktop entry. That installation also loaded 397 cloud photos, opened a
full-size photo and responded to the UI probe. GrowthSDK was absent from its
process mappings. This establishes a working library path; it does not establish
GPU support, accurate color transforms, editing/export, or upload of changes.

## Subsequent GPU comparison and final installation

The operator confirmed editing works, but reported slowness and pointer jumping
in the camera-profile selector. Closed the regular installation normally
(launcher exit status 0), stopped its remaining helpers, and saved a private
`working-library-staging-20260916` prefix snapshot. The original authenticated
snapshot was retained separately.

Created another isolated copy from that working snapshot. Changed only the
Direct3D 12 DLL pair and its load overrides, using the vkd3d-proton binaries
inside the already checksum-pinned GE-Proton11-6 archive. Camera Raw recognized
the Intel Panther Lake GPU and completed `cr_gpu_test::RunSanity` successfully,
with GPU3 and GPU4 hard/soft results all `success`. The app remained responsive
and displayed cloud photos. This verifies GPU initialization; performance was
not benchmarked. The profile-selector pointer jump remains unresolved.

Added `repair-d3d12` to reproduce that installation using the verified archive,
retain original DLLs under the selected prefix's `repairs/d3d12/`, and apply
Lightroom-only native overrides. Tests verify prefix isolation, preservation of
the first backup across repeated repairs, and refusal to change a prefix if the
archive lacks one DLL. All 12 launcher tests pass.

Applied the repair to the regular staging prefix. Closed the GPU test normally,
stopped its helpers, and launched the regular installed desktop entry through
Hyprland (`hl.exec_cmd` with `gio launch`). This avoids tying the GUI lifetime
to the diagnostic command process. The normal desktop launch restored the
signed-in library, responded to `WM_NULL` in 1 ms, and again reported successful
Camera Raw GPU sanity tests. The window was on workspace 10 (Super+0).

Final private evidence: `logs/20260916-192106-lightroom.log`,
`logs/20260916-final-desktop-gpu.png`, and the regular prefix's Camera Raw log.
No raw credentials, libraries, photos or screenshots are included in Git.
