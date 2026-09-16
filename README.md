# omarchy-lightroom-cc

An open-source compatibility experiment by **[Paul Zammit](https://github.com/LamplighterPaul)**
to run Adobe **Lightroom CC (cloud)** locally on Omarchy, with an isolated Wine
setup and desktop integration.

**Status · 16 September 2026 · cloud library loads; sign-in survives restart**

Genuine Adobe sign-in **succeeded**, and Lightroom now loads the cloud library
and opens full-size photos. Disabling the optional AdobeGrowthSDK for Lightroom
avoids the observed post-sign-in hang. A clean exit and restart preserved sign-in
and restored the library without another login. The operator confirms basic
editing works. Camera Raw now detects the Intel GPU and passes its GPU sanity
tests with vkd3d-proton. Full editing/export validation is still pending.

## What works so far

- Download and stage the genuine Lightroom 9.5.1 Windows payload directly from
  Adobe, without installing the Creative Cloud desktop UI.
- Decode Adobe's ZIP/raw-LZMA2 payload and verify pinned download checksums.
- Clear the MSVCP140 startup crash with Microsoft's VS2022 redistributables.
- Pass a missing Direct2D startup effect using a source-built experimental patch.
- Render Adobe's sign-in form using Wine Staging 11.17 and Adobe's CEF/NGL helpers.
- Complete subscription sign-in and return to the native Windows Lightroom app.
- Load cloud photos and albums, open photos, and retain sign-in across restart.
- Avoid the post-sign-in hang with a persistent, Lightroom-only GrowthSDK override.
- Initialize Camera Raw's Intel GPU path using vkd3d-proton's Direct3D 12 DLLs.
- Launch from an Omarchy desktop entry that remembers the selected Wine runner.

## Remaining limitations

| Area | Current result |
| --- | --- |
| Main UI | Responsive with optional AdobeGrowthSDK disabled; library and photo view verified. Underlying heap fault remains unresolved. |
| Camera Raw GPU | Intel GPU recognized; GPU sanity tests pass. Speedup not benchmarked. |
| Color management | Experimental Direct2D effect is a pass-through, not a color transform. |
| Import, edit, export | Basic editing confirmed by the operator. Comprehensive tool and export tests remain. |
| Input and performance | Operator reported slowness and pointer jumping in the camera-profile selector before the GPU comparison. Pointer issue remains unresolved. |
| Persistence and cloud sync | Sign-in persists after exit/restart; cloud library downloads. Edit persistence and upload not verified. |
| Clean installation and packaging | Not reproduced; no production package yet. |

Full results and the restart point are in **[Status and validation](docs/validation.md)**.
Follow the **[issue tracker](https://github.com/LamplighterPaul/omarchy-lightroom-cc/issues)**
for remaining work.

## Try or contribute

This is a developer preview for people investigating compatibility. A genuine
Adobe subscription and interactive sign-in are required. Adobe does not support
this Linux configuration. Windows APIs run through Wine; this is not a Linux port.

See **[Development setup](docs/setup.md)** for commands and dependencies,
**[diagnostics](diagnostics/README.md)** for inspection tools, and
**[CONTRIBUTING.md](CONTRIBUTING.md)** for reporting reproducible results.

```sh
git clone https://github.com/LamplighterPaul/omarchy-lightroom-cc.git
cd omarchy-lightroom-cc
make check
```

Full GE-Proton through UMU and Steam Linux Runtime was tested on both Xwayland
and native Wayland. Its sign-in window stayed blank. The successful sign-in
combination used standalone Wine Staging, DXVK and Adobe's own Chromium helper.
Android and macOS compatibility remain untested fallback ideas. Photoshop has
not been validated by this project.

## Credits and license

Original launcher, diagnostics, build scripts, tests and documentation:
**Copyright © 2026 Paul Zammit and contributors, [MIT](LICENSE)**.

The Direct2D experiment includes work from **6im0n, sander110419 and the Wine
project**, with their notices and licenses preserved. See
**[THIRD_PARTY.md](THIRD_PARTY.md)** for source revisions, license scope, runtime
credits and inspiration from Proton, SteamOS, CachyOS, Bazzite and Omarchy.
See **[research notes](docs/research.md)** for the direct-download findings.

This repository contains source and documentation. Adobe applications,
Microsoft redistributables, runtime archives, credentials, photos and signed-in
Wine environments are not included. Downloaded components retain their own
licenses. Adobe, Lightroom and Creative Cloud are trademarks of Adobe Inc.;
this is an independent project.
