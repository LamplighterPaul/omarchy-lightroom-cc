# Third-party sources, licenses and credits

This project was created by **Paul Zammit**. Original project code and
writing are MIT-licensed; see [LICENSE](LICENSE). The work below made the
experiment possible. Inclusion in this list does not imply endorsement.

## Source included in this repository

### Experimental Direct2D patch

`patches/d2d1-colormanagement-experimental.patch` extracts the `effect.c` hunks
from [6im0n/lightroom-classic-on-linux's d2d1-lightroom.patch](https://github.com/6im0n/lightroom-classic-on-linux/blob/7df91da9301dfb31eb228abac76972a9081e3fd2/resources/patches/wine/d2d1-lightroom.patch),
revision `7df91da9301dfb31eb228abac76972a9081e3fd2`. Other hunks were omitted.

- Recipe/patch additions: copyright © 2026 **6im0n, sander110419 and contributors**.
  Their [MIT notice](LICENSES/lightroom-classic-on-linux-MIT.txt) is preserved.
- Related original CC recipe: copyright © 2026 **sander110419 and contributors**.
  Its [MIT notice](LICENSES/lightroom-cc-on-linux-MIT.txt) is also preserved.
- Wine code/context: **Wine project authors**, including `effect.c` copyright
  © 2018 **Nikolay Sivov for CodeWeavers**; LGPL-2.1-or-later.
  See [Wine notice](LICENSES/Wine-NOTICE.txt) and [LGPL 2.1](LICENSES/LGPL-2.1.txt).

The patch targets [Wine revision 2cac6ccf33c0807f374dc96f5a20e35a2da86157](https://github.com/wine-mirror/wine/tree/2cac6ccf33c0807f374dc96f5a20e35a2da86157)
(Wine 11.10). The source-built DLL remains a Wine-derived LGPL work; this
project's MIT license does not replace those terms. The build script retrieves
that exact source revision and records patch/DLL hashes locally. No built DLL
is distributed here.

The inherited patch comment claiming the effect is never invoked while editing
has **not** been verified. The patch is a pass-through, not color management.

## Downloaded components and development tools

These are fetched or used locally, not vendored. Upstream licenses and notices
continue to apply. Pinned downloadable artifacts are listed in
[manifest.json](manifest.json); local build-package hashes are in
[build-toolchain.json](docs/build-toolchain.json).

| Project / supplier | Use and source |
| --- | --- |
| [Wine](https://www.winehq.org/) / [Wine Staging](https://github.com/wine-staging/wine-staging) | Windows compatibility; Staging 11.17 produced the successful sign-in. Wine is LGPL-2.1-or-later. |
| [PhialsBasement/wine-adobe-installers](https://github.com/PhialsBasement/wine-adobe-installers) | Initial Adobe Wine 11.10 runner; Adobe Proton 10 also evaluated. Consult its source and component notices. |
| [DXVK](https://github.com/doitsujin/dxvk) | Direct3D 11/DXGI over Vulkan; pinned 2.7.1 comparison. Copyright Philip Rebohle and contributors, zlib license. |
| [vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton) | Direct3D 12 over Vulkan; DLL pair from the pinned GE-Proton11-6 bundle. Successfully initializes Camera Raw's Intel GPU path. Upstream component licenses apply; no binaries are included here. |
| [Valve Proton](https://github.com/ValveSoftware/Proton) / [GE-Proton](https://github.com/GloriousEggroll/proton-ge-custom) | Full GE-Proton11-6 comparison; Wine and additional components with their respective licenses. |
| [UMU launcher](https://github.com/Open-Wine-Components/umu-launcher) | Launches the full Proton comparison outside Steam. |
| [Steam Linux Runtime](https://gitlab.steamos.cloud/steamrt/steam-runtime-tools) | Runtime container used by UMU; component licenses apply. |
| [Winetricks](https://github.com/Winetricks/winetricks) | Dependency setup, including fonts, MSXML, GDI+, Adobe Type Manager library and DXVK. Its downloads retain their own licenses. |
| [Wine Gecko](https://wiki.winehq.org/Gecko) | Legacy embedded browser support evaluated during setup. |
| [cabextract](https://www.cabextract.org.uk/) / [7-Zip](https://www.7-zip.org/) | Extract official dependency payloads for local use. |
| [Arch Linux](https://archlinux.org/) / [Omarchy](https://github.com/basecamp/omarchy) | Signed package sources and target desktop environment. Signature checks were performed locally; the launcher pins SHA-256 hashes. |
| [GCC](https://gcc.gnu.org/), [MinGW-w64](https://www.mingw-w64.org/), [GNU Make](https://www.gnu.org/software/make/), [Flex](https://github.com/westes/flex), [GNU Bison](https://www.gnu.org/software/bison/) | Build the Wine patch and Windows diagnostic helper. |
| [GDB](https://www.sourceware.org/gdb/), [Python](https://www.python.org/), [Node.js](https://nodejs.org/), [curl](https://curl.se/), [libarchive](https://www.libarchive.org/), [Info-ZIP](https://infozip.sourceforge.net/) | Launcher, tests, debugging, download and archive tooling. |
| [Mesa](https://www.mesa3d.org/), [Hyprland](https://hypr.land/), [Xwayland](https://wayland.freedesktop.org/xserver.html) | Host graphics and windowing used for the experiments. |
| [Adobe](https://www.adobe.com/products/photoshop-lightroom.html) | Proprietary Lightroom and CEF/NGL authentication components, downloaded from Adobe. A valid subscription is required. No Adobe application binaries or authenticated profiles are distributed. |
| [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) / [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) | Official proprietary runtime downloads. Microsoft terms apply; binaries are not included. |

The Adobe helper embeds Chromium/CEF and includes its own upstream notices.
It remains an Adobe-distributed component; the open-source launcher does not
make Adobe Lightroom open source.

## Research and inspiration

- [sander110419/lightroom-cc-on-linux](https://github.com/sander110419/lightroom-cc-on-linux/tree/04eacfdafd52742cd851586aea7116045b928513):
  prior cloud Lightroom recipe. Its reported success is not our own validation.
- [6im0n/lightroom-classic-on-linux](https://github.com/6im0n/lightroom-classic-on-linux/tree/7df91da9301dfb31eb228abac76972a9081e3fd2):
  Arch/Intel findings and inspectable patches. Classic is a different app.
- [ckamte/adobe-packager-windows](https://github.com/ckamte/adobe-packager-windows):
  source reading identified Adobe's public catalog endpoint. Its downloader was
  not executed or copied into this launcher.
- [Wine Staging investigation](https://www.patreon.com/winestaging/posts/investigation-of-160397129):
  identified misleading COM/licensing assumptions in the earlier recipe.
  We did not apply the guessed RealTimeStylus stub or mfplat binary patch.
- [Proton](https://github.com/ValveSoftware/Proton),
  [SteamOS](https://store.steampowered.com/steamos/) and
  [Valve's published source](https://repo.steampowered.com/): inspiration for
  per-application compatibility and controlled runtimes. SteamOS includes open
  Linux components alongside proprietary Steam software; it is not one uniformly
  open-source application stack.
- [CachyOS](https://wiki.cachyos.org/configuration/gaming/) and
  [Bazzite](https://docs.bazzite.gg/Installing_and_Managing_Software/software-intro/):
  inspiration for selectable runtimes, current graphics drivers and convenient
  desktop installation. No distribution-specific code was copied.
- [vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton) and
  [Adobe's GPU requirements](https://helpx.adobe.com/lightroom/desktop/kb/lightroom-gpu-faq.html):
  references for the Direct3D 12 comparison. Our Intel GPU initialization and
  Camera Raw sanity-test results are recorded in [validation](docs/validation.md).
- [Darling](https://www.darlinghq.org/) and Android Lightroom: fallback ideas only;
  neither was validated by this project.

Grok CLI returned no substantive X research. agy research was blocked by its
read permission policy. Neither supplied usable YouTube transcript evidence.
