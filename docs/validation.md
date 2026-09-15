# Status and validation

**15 September 2026 — development paused after successful Adobe authentication.**
The main Lightroom UI hangs. This is not a working photo-editing release.

## Tested configuration

| Component | Observed configuration |
| --- | --- |
| Desktop | Omarchy / Hyprland / Xwayland |
| Hardware | Intel Core Ultra 7 355, Panther Lake integrated graphics, approximately 32 GB RAM |
| Host graphics | Mesa 26.2.2, kernel 7.2.3 |
| Lightroom | Cloud Lightroom 9.5.1.202608151945, Camera Raw 18.5.1 |
| Successful authentication runner | Wine Staging 11.17, separate prefix |
| Direct3D 11 | DXVK 2.7.1 |
| Direct2D | Source-built Wine 11.10 with experimental ColorManagement pass-through |
| Authentication | Adobe CEF/NGL extracted from official Creative Cloud 6.10.0.252.41 archive |
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

## Current blocker: unresponsive main window

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
No all-thread backtrace has yet identified the heap-lock owner’s blocked call.

**Parked state:** Lightroom, its debugger and the experiment's Wine processes
were stopped. An authenticated prefix snapshot is retained privately on the
development machine and is not part of this repository.

## GPU evidence

Camera Raw's log reported `GPU Init Status (part 1): I1_Failed`,
`GPU system count: 0`, `GPU device count: 0`, `fail_no_gpu2`, and
`Invalid GPU system`. DXVK sees the Intel Vulkan device, which does not establish
that Camera Raw can use it. The staging run loaded Wine's builtin `d3d12.dll`.

A comparison with vkd3d-proton's native `d3d12.dll` and `d3d12core.dll` is a
**proposed next experiment**, not a demonstrated fix. Isolate the UI hang before
changing the GPU stack so the results remain interpretable.

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

Temporary WebView2 debugger/sandbox overrides were removed from baseline
prefixes. Adobe's CEF helper itself supplies `--no-sandbox` to its child processes.
The browser's long-term suitability and update path have not been established.
No guessed RealTimeStylus COM stub or mfplat binary patch from earlier recipes
was applied; see [research notes](research.md).

## Release gates / next work

- [ ] Diagnose the post-authentication hang and verify sustained UI responsiveness.
- [ ] Establish a usable Camera Raw GPU path and measure it on this Intel GPU.
- [ ] Replace or validate the Direct2D workaround against reference color output.
- [ ] Import disposable JPEG and camera RAW files.
- [ ] Verify exposure, white balance, crop, masking and undo.
- [ ] Export JPEG/TIFF and compare pixels and embedded profiles with a reference.
- [ ] Close/reopen and confirm edits persist.
- [ ] Verify upload and edits on Lightroom web or another device.
- [ ] Test remove/heal, AI tools, offline/reconnect and sustained large-image editing.
- [ ] Verify HiDPI, keyboard, file picker and multiple monitors.
- [ ] Reproduce setup from a clean environment before building an Arch/Omarchy package.

When resumed, start with `--runner staging native-debug` and inspect thread
stacks at the hang. Preserve authentication privately. Record app/runtime/driver
versions and exact reproduction steps for every comparison. Do not report
editing, export, color accuracy or cloud sync as working until those checks pass.

## Publication checks

At this snapshot, all 10 launcher unit tests pass (`make check`). Python syntax
checks and the Node diagnostic syntax check also pass. These checks cover code
and payload handling, not Adobe editing or runtime compatibility.
