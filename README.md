# omarchy-lightroom-cc

Run the Windows version of Adobe **Lightroom CC (cloud)** locally on Omarchy,
through a dedicated Wine environment, with desktop integration.

**Status: Adobe sign-in succeeded and returned to Lightroom on the target
machine with Wine Staging 11.17 and Adobe's CEF/NGL components. Editing, export, color
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

### Observed working sign-in route

On the prepared environment above, the Adobe Wine runner's WebView2 path
remained blank. This separate runtime and Adobe browser combination displayed
the actual Adobe sign-in form:

```sh
omarchy-lightroom-cc stop
omarchy-lightroom-cc repair-dxvk
omarchy-lightroom-cc stage-staging
omarchy-lightroom-cc --runner staging initialize-runner
omarchy-lightroom-cc --runner staging stage-adobe-browser
omarchy-lightroom-cc --runner staging run
omarchy-lightroom-cc --runner staging integrate
```

`stage-adobe-browser` extracts only Adobe's Chromium engine (CEF) and sign-in
helper (NGL) from the official, checksum-pinned offline archive. It does not
install Creative Cloud desktop. The desktop entry remembers the selected
runner. This result was obtained incrementally; clean-install reproduction and
authenticated editing remain release requirements.

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

### Full Proton comparison

With the original Lightroom prefix prepared and stopped:

```sh
omarchy-lightroom-cc stop
omarchy-lightroom-cc stage-proton
omarchy-lightroom-cc --runner proton run-debug
omarchy-lightroom-cc --runner proton stop
omarchy-lightroom-cc --runner proton --graphics wayland run-debug
```

This stages checksum-pinned GE-Proton11-6 and UMU 1.4.4, then copies the
original prefix into `experiments/proton-ge/prefix`. UMU downloads and verifies
the matching Steam Linux Runtime on first launch. It does not add an app to
Steam or change the system Wine installation. The first Xwayland Proton test
still showed a white sign-in window; native Wayland is being investigated.

The Wine Staging route above currently has the best observed result. Full
Proton with Adobe CEF was also tested and its sign-in window stayed blank.

### Other platforms

Android Lightroom is the next planned fallback. This machine's Android emulator
supports arm64 translation, but Lightroom has not been installed or tested there.
Darling's macOS compatibility layer is an exploratory last option; we have no
verified evidence of current Mac Lightroom working through it.
