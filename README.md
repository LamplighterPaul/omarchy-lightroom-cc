# omarchy-lightroom-cc

Run the Windows version of Adobe **Lightroom CC (cloud)** locally on Omarchy,
through a dedicated Wine environment, with desktop integration.

**Status: experimental setup in development. Lightroom editing, export, color
accuracy and cloud sync have not yet been verified on the target machine.**
This is not a Linux port of Adobe Lightroom or an Adobe-supported platform.
A valid Adobe subscription and interactive Adobe sign-in are required.

## Start

```sh
make install
omarchy-lightroom-cc doctor
omarchy-lightroom-cc prepare
python3 scripts/build-d2d1.py
omarchy-lightroom-cc experiment-d2d
omarchy-lightroom-cc stage-lightroom
omarchy-lightroom-cc repair-webview
```

This fetches Lightroom directly from Adobe and decodes its installation payload.
Creative Cloud desktop is optional. Adobe sign-in and subscription validation
still apply. Then:

```sh
omarchy-lightroom-cc run
omarchy-lightroom-cc integrate
```

The Direct2D experiment is currently required to get past a startup error.
Its pass-through effect does not implement color management. Build requirements
are GCC, make, flex, bison and the mingw-w64 toolchain. The script accepts a
user-local toolchain in `$LRCC_DATA/tools/usr/bin`, as used on the development
machine. `restore-d2d` rolls this experiment back (and closes this Wine prefix).

The installer and app are still being debugged. These commands describe the
intended workflow, not a claim that the whole workflow currently passes.

Other commands: `status`, `cc`, `stop`, `run-debug`, `repair-vcrun`,
`repair-browser` (Wine Gecko), and `repair-webview` (Microsoft WebView2). `install-cc /absolute/path/Setup.exe`
allows testing Adobe's online bootstrapper. Logs live under
`~/.local/share/omarchy-lightroom-cc/logs` and can contain private account or
file details; review them before sharing.

## Design

- A pinned, checksum-verified Wine 11.10 Adobe runner; no system Wine replacement.
- A dedicated C: drive and registry under `~/.local/share/omarchy-lightroom-cc`.
  A Wine prefix is configuration separation, **not a security sandbox**.
- Project-local copies of cabextract and Winetricks from signed Omarchy/Arch packages.
- Adobe installers fetched directly from Adobe; no Adobe binaries or user data in Git.
- Xwayland first on Hyprland. DXVK translates Direct3D to Vulkan.
- Small compatibility fixes added only when local failures establish the need.
- One runtime per environment; Photoshop/alternate runner experiments stay separate.

`LRCC_DATA` overrides the data directory for development. `LRCC_WINEDEBUG`
overrides Wine logging. Python 3.12+, curl, bsdtar, unzip, Xwayland and a working
Vulkan driver are needed. Microsoft C++ redistributables are downloaded directly from Microsoft with
pinned hashes. Other dependencies use Winetricks checksum checks; changed
upstream downloads fail closed.

## Prior art and inspiration

- [Lightroom CC Wine recipe](https://github.com/sander110419/lightroom-cc-on-linux),
  reviewed at `04eacfdafd52742cd851586aea7116045b928513`.
- [Lightroom Classic on Linux](https://github.com/6im0n/lightroom-classic-on-linux),
  reviewed at `7df91da9301dfb31eb228abac76972a9081e3fd2`: newer Creative Cloud fixes,
  Arch/Intel evidence, and source-available Direct2D patches. Classic success
  does not establish cloud Lightroom compatibility.
- [Adobe Wine patches](https://github.com/PhialsBasement/wine-adobe-installers/releases),
  both Wine 11.10 and Proton 10 runtimes.
- [CachyOS](https://wiki.cachyos.org/configuration/gaming/): side-by-side Wine
  runners, per-app configuration, and current graphics drivers.
- [Bazzite](https://docs.bazzite.gg/Installing_and_Managing_Software/software-intro/):
  convenient application setup and limiting changes to the host OS.
- [Proton](https://github.com/ValveSoftware/Proton) and
  [UMU](https://github.com/Open-Wine-Components/umu-launcher): reproducible
  runtime environments and app-specific compatibility fixes.

## Release requirements

See [validation.md](docs/validation.md). Distribution should package this launcher
and its open-source fixes, not Adobe applications or signed-in Wine environments.
A normal Arch package with a desktop entry is the initial Omarchy integration
target. A shell plugin is only useful if ongoing shell UI is needed.

## Direct download findings

See [research.md](docs/research.md) for the Adobe catalog and payload format.
The app has reached its main window and browser sign-in on the target machine
without Creative Cloud desktop. This does not yet establish successful login,
editing, export or cloud synchronization.

## Alternatives

Android Lightroom is the next planned fallback. This machine's Android emulator
supports arm64 translation, but Lightroom has not been installed or tested there.
Darling's macOS compatibility layer is an exploratory last option; we have no
verified evidence of current Mac Lightroom working through it.
