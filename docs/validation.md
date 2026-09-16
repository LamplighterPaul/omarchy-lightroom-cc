# Status and validation

**16 September 2026 — cloud library loads and sign-in survives restart.**
Disabling optional AdobeGrowthSDK avoids the observed UI hang. The operator
confirmed basic editing, and vkd3d-proton passed Camera Raw's GPU sanity tests.
Full editing and export validation is still pending; this is not a production release.

## Tested configuration

| Component | Observed configuration |
| --- | --- |
| Desktop | Omarchy / Hyprland / Xwayland |
| Hardware | Intel Core Ultra 7 355, Panther Lake integrated graphics, approximately 32 GB RAM |
| Host graphics | Mesa 26.2.2, kernel 7.2.3 |
| Lightroom | Cloud Lightroom 9.5.1.202608151945, Camera Raw 18.5.1 |
| Successful authentication runner | Wine Staging 11.17, separate prefix |
| Direct3D 11 | DXVK 2.7.1 |
| Direct3D 12 | vkd3d-proton DLL pair from checksum-pinned GE-Proton11-6, under Wine Staging |
| Direct2D | Source-built Wine 11.10 with experimental ColorManagement pass-through |
| Authentication | Adobe CEF/NGL extracted from official Creative Cloud 6.10.0.252.41 archive |
| Post-sign-in workaround | Empty AdobeGrowthSDK DLL override under Wine AppDefaults for lightroom.exe |
| Browser engine | Adobe helper reports Chromium 116.0.5845.190 |

Download URLs and SHA-256 values are in [manifest.json](../manifest.json).
Local compiler package hashes are in [build-toolchain.json](build-toolchain.json).
The successful route was prepared incrementally. These observations do not prove
that the documented commands reproduce it on a clean machine.

## Fixed or demonstrated

1. **Direct installation payload:** fetched cloud Lightroom from Adobe's catalog;
   decoded backslash ZIP paths and nested raw LZMA2 payloads into valid PE files.
   Creative Cloud desktop is not installed. Installer registration is incomplete.
2. **MSVCP140 startup crash:** replacing the older runtime with genuine Microsoft
   VS2022 redistributables and native overrides cleared the observed crash.
3. **Direct2D startup error:** registered the missing ColorManagement effect
   `{1a28524c-fdd6-4aa4-ae8f-837eb8267b37}` using a source-built pass-through.
   This clears startup only; color transforms remain unimplemented by this patch.
4. **Authentication rendering:** Wine Staging plus Adobe CEF/NGL displayed the
   actual sign-in form. Both direct visual inspection and the operator confirmed it.
5. **Authentication return:** the subscribed user completed sign-in and returned
   to Lightroom; the helper window closed. No licensing code was modified.
6. **Desktop integration:** the launcher records the chosen runner in its desktop
   entry. Runtimes and prefixes are user-local; system Wine was not replaced.
7. **Cloud library:** with GrowthSDK disabled, 397 cloud photos and the album list
   loaded. Full-size photos opened; the operator also confirmed the app worked.
8. **Sign-in persistence:** closed Lightroom using its normal window-close path
   (launcher exited with status 0), stopped remaining prefix helpers, then
   relaunched without the temporary environment override. The persistent
   per-application registry setting was sufficient. No login prompt appeared;
   the library and photo view returned. Credential contents were not inspected.
9. **Basic editing:** the Edit panel opens. The operator confirmed it works,
   while reporting slowness and pointer jumping in the camera-profile selector.
   This is not a tool-by-tool or exported-pixel validation.

## Original blocker and verified workaround

After successful authentication the main window stopped accepting clicks and
resize updates. `ui responsiveness` returned Windows timeout error 1460 for a
`WM_NULL` message sent with `SendMessageTimeoutW`. Memory was approximately
1.0–1.1 GiB. A short sample showed almost no CPU activity, but overlapped a
failed debugger attachment and is not a performance benchmark.

A restart under native GDB produced repeated Wine lock timeouts:

```text
main process heap section: thread 0024 blocked by 0320
main process heap section: several worker threads also blocked by 0320
loader_section: blocked by 034c
fls_section: blocked by 02c0
```

These are symptoms consistent with a deadlock; the underlying cause and complete
lock cycle have not been established. Thread IDs are specific to that run.
The [16 September follow-up](hang-investigation-2026-09-16.md) captured native
all-thread backtraces and located the heap-lock owner in `NtWaitForSingleObject`.
Saved Windows exception evidence points to an access violation in Wine's heap
code followed by Adobe crash handling. The original fault's cause is unresolved;
the Windows stack scan is not a validated unwind.

`repair-growth-sdk` now avoids this hang by disabling the optional SDK only for
Lightroom. The isolated copy passed restart testing, and the same setting was
applied to the regular staging prefix and its desktop launcher. The regular
installation also loaded the cloud library without asking for sign-in.

The original authenticated prefix snapshot remains private and unchanged.
Diagnostic traces and screenshots are private local evidence, not repository
assets. See the [16 September investigation](hang-investigation-2026-09-16.md)
for the distinction between the workaround and the unresolved heap fault.

## GPU evidence

Before the D3D12 repair, Camera Raw's log reported `GPU Init Status (part 1): I1_Failed`,
`GPU system count: 0`, `GPU device count: 0`, `fail_no_gpu2`, and
`Invalid GPU system`. DXVK sees the Intel Vulkan device, which does not establish
that Camera Raw can use it. The staging run loaded Wine's builtin `d3d12.dll`.

After isolating the hang with GrowthSDK disabled, compared the same signed-in
configuration with vkd3d-proton's native `d3d12.dll` and `d3d12core.dll` from the
pinned GE-Proton11-6 archive. Camera Raw reported:

```text
Loaded GPU system: DirectX
GPU device count: 1
GPU device names: Intel(R) Graphics (PTL)
Completed cr_gpu_test::RunSanity successfully.
GPU Init Status (part 2): I4_GPU4
GPU3 Hard Status Result (part 2): success
GPU3 Soft Status Result (part 2): success
GPU4 Hard Status Result (part 2): success
GPU4 Soft Status Result (part 2): success
```

The library and photos remained available. `repair-d3d12` now reproduces this
DLL installation with per-application overrides and backups in the selected
prefix. This verifies GPU initialization, not a measured speedup or every
GPU-accelerated editing tool. Masking inference still selects the CPU for this
Intel GPU; AI masking has not been validated. No vendor spoof was applied.
The regular installation was then launched through its installed desktop entry;
it retained sign-in, loaded the library and repeated the successful GPU checks.

The pointer jump has not been reliably reproduced. Global Hyprland pointer and
scaling settings were left unchanged; the monitor uses scale 2 and Xwayland
`force_zero_scaling` is enabled. Do not claim that GPU initialization fixes it.

## Other combinations tested

| Combination | Observed result |
| --- | --- |
| Adobe Wine 11.10 + WebView2 153 | White sign-in window; GPU child failures. |
| WebView2 148 + effective registry rendering policies | White window; GPU fatal errors persisted. |
| WebView2 environment-variable flags | Ignored by the app; not valid rendering comparisons. |
| GE-Proton11-6 + UMU 1.4.4 + Steam Runtime 4, Xwayland | White sign-in window; one run fell back to IE and Adobe's “Update your browser” page. |
| Same full Proton stack, native Wayland | Blank, oversized sign-in surface. |
| Full Proton + Adobe CEF/NGL | Browser context initialized, visible page remained blank. |
| Wine Staging 11.17 + Adobe CEF/NGL | Sign-in succeeded; main Lightroom UI then hung. |
| Same, with GrowthSDK disabled | Cloud library and photo view load; sign-in persists across restart. |
| Same, plus native vkd3d-proton D3D12 | Intel GPU recognized and Camera Raw GPU sanity tests pass. |

Temporary WebView2 debugger/sandbox overrides were removed from baseline
prefixes. Adobe's CEF helper itself supplies `--no-sandbox` to its child processes.
The browser's long-term suitability and update path have not been established.
No guessed RealTimeStylus COM stub or mfplat binary patch from earlier recipes
was applied; see [research notes](research.md).

## Release gates / next work

- [x] Avoid the post-authentication hang and verify library/UI responsiveness across restart.
- [ ] Diagnose the underlying heap fault with GrowthSDK enabled.
- [x] Establish a Camera Raw GPU path that passes its sanity tests on this Intel GPU.
- [ ] Measure editing performance on this Intel GPU.
- [ ] Replace or validate the Direct2D workaround against reference color output.
- [ ] Import disposable JPEG and camera RAW files.
- [ ] Verify exposure, white balance, crop, masking and undo.
- [ ] Export JPEG/TIFF and compare pixels and embedded profiles with a reference.
- [ ] Close/reopen and confirm edits persist.
- [ ] Verify upload and edits on Lightroom web or another device.
- [ ] Test remove/heal, AI tools, offline/reconnect and sustained large-image editing.
- [ ] Verify HiDPI, keyboard, file picker and multiple monitors.
- [ ] Reproduce setup from a clean environment before building an Arch/Omarchy package.

For further heap diagnosis, use an isolated copy with GrowthSDK enabled and
start with `--runner staging native-debug`. Preserve authentication privately. Record app/runtime/driver
versions and exact reproduction steps for every comparison. Do not report
editing, export, color accuracy or cloud sync as working until those checks pass.

## Publication checks

At this snapshot, all 12 launcher unit tests pass (`make check`). Python syntax
checks and the Node diagnostic syntax check also pass. These checks cover code
and payload handling, not Adobe editing or runtime compatibility.
