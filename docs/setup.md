# Development setup

Experimental instructions, recorded on 15 September 2026. Sign-in succeeded on
one incrementally prepared machine; the main UI then hung. A clean installation
has not been reproduced. Read [current status](validation.md) before trying this.

Run these commands from a checkout of this repository.

## Prepare

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

### Inspect the hang after sign-in

After the staging route returns to Lightroom, the main window is expected to
stop accepting clicks. Do not change the GPU stack in the same comparison.
Install `gdb` first. Launch Wine as GDB's child so ptrace_scope=1 hosts can
still interrupt the hung process:

```sh
omarchy-lightroom-cc --runner staging stop
omarchy-lightroom-cc --runner staging native-debug
```

Run that in an interactive terminal. At the hang, press Ctrl-C, then:

```
thread apply all bt
```

The goal is to identify the owner of the Wine heap lock and the call that
thread is blocked on. Full notes live in [diagnostics](../diagnostics/README.md)
and [issue #1](https://github.com/LamplighterPaul/omarchy-lightroom-cc/issues/1).
Review debugger output before sharing; it can contain private paths. Do not
attach an authenticated prefix. `native-debug` does not support the Proton
runner.

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

## Full Proton comparison

After preparing and stopping the original environment:

```sh
omarchy-lightroom-cc stop
omarchy-lightroom-cc stage-proton
omarchy-lightroom-cc --runner proton run-debug
omarchy-lightroom-cc --runner proton stop
omarchy-lightroom-cc --runner proton --graphics wayland run-debug
```

This uses GE-Proton11-6 through UMU 1.4.4 and Steam Linux Runtime 4, with a
separate prefix. Both Xwayland and native Wayland were tested. Neither produced
a working sign-in flow here; Wine Staging with Adobe CEF did.

## Stop

```sh
omarchy-lightroom-cc --runner staging stop
```

Select the same runner you launched. Stopping closes processes in that runner's
prefix. Installed data remains under `$LRCC_DATA` (default:
`~/.local/share/omarchy-lightroom-cc`). Keep that directory private: it can contain
account credentials, photo data and logs. Do not commit or redistribute it.
