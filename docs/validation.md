# Release gate

Target: Omarchy/Hyprland, Intel Panther Lake, Mesa 26.2.2, kernel 7.2.3,
approximately 32 GB RAM. User has a cloud Lightroom subscription.

Record app version, runner hash, driver version and exact reproduction steps
with each result. Use disposable photos until persistence and sync are verified.

| Check | Status |
| --- | --- |
| Adobe Wine 11.10 archive checksum and --version | Passed |
| Adobe Proton 10 archive checksum and --version | Passed (alternate experiment) |
| cabextract/Winetricks package signatures | Passed against local Arch keyring |
| Dedicated prefix creation and dependency installation | Passed |
| Creative Cloud UI, genuine login and app catalog | Offline UI failed; optional direct route used |
| Stage and launch cloud Lightroom | Main window and genuine Adobe sign-in form render under Wine Staging + Adobe CEF |
| Authenticate the subscribed account | Passed: user confirmed successful sign-in and return to Lightroom |
| Import JPEG and camera RAW | Pending |
| Exposure, white balance, crop, local mask and undo | Pending |
| Export JPEG/TIFF and compare pixels/profiles with a reference | Pending |
| Close/reopen, edits persist | Pending |
| Upload test photo and verify edits on Lightroom web/another device | Pending |
| GPU acceleration, large image and sustained editing | Pending |
| Remove/heal, AI tools, offline/reconnect | Pending |
| HiDPI, keyboard, file picker, multiple monitors | Pending |
| Reproduce installation from a clean environment | Pending |

The original CC recipe uses a no-op Direct2D ColorManagement effect. Its claim
that this only satisfies a startup probe is not proof of correct display color.
Any use of this workaround must remain explicitly experimental until tested.

Independent negative evidence: a [CachyOS tester](https://discuss.cachyos.org/t/lightroom-on-linux-progress-in-2026/30426)
installed all apps but reported CC crashing soon after launch and Photoshop
crashing immediately. Launch screenshots alone do not pass this release gate.

Research tools: Grok was invoked for X/web research but returned no substantive
findings. agy headless research was blocked by its read_url permission policy.
No claim of verified X reports or YouTube transcripts is made.

## Local experiment, 2026-09-15

- Direct Adobe catalog selected LRCC 9.5.1.202608151945. Downloaded the
  2,518,535,915-byte Windows package directly from ccmdls.adobe.com using the
  Creative Cloud user agent. SHA-256 is pinned in manifest.json.
- Adobe's ZIP entries use backslash paths and an additional raw LZMA2 stream
  inside each stored entry. The launcher decodes this; the executable is a
  valid PE file, 27,384,816 bytes. No Adobe licensing code was modified.
- Creative Cloud desktop remains uninstalled. The offline installer failed to
  render, which motivated testing the directly staged Lightroom payload.
- First Lightroom launch crashed in MSVCP140. Upgrading Microsoft's native
  redistributables from VS2019 to VS2022 cleared that crash.
- Next startup stopped in a Direct2D initialization dialog. Wine logged the
  missing ColorManagement effect GUID. Built the effect-only workaround from
  Wine 11.10 source locally; no downloaded third-party replacement DLL used.
- With that workaround, Lightroom creates its main window. Its console then
  reports no installed WebView2 runtime. Sign-in, editing and sync remain
  unverified; window creation is not a working-app result.

Build tools were extracted from signed Arch/Omarchy packages into the user
application directory. No system Wine or package-manager changes were made.
Compiler package hashes are in build-toolchain.json. Local logs and binaries
are deliberately excluded from this repository.

- Microsoft WebView2 153.0.4234.32 installed successfully from the official
  standalone installer. The missing-runtime message is gone. User observed
  Adobe browser sign-in opening; successful account return is still pending.

### Remaining sign-in failure

The user sees a splash screen followed by a white window. The main menus and
panels render, but the embedded WebView2 sign-in window does not. WebView2
Crashpad reports include `GPU process isn't usable. Goodbye.` Browser login
opened once but did not establish a verified signed-in session.

Environment-variable experiments with `--disable-gpu`, `--no-sandbox`,
`--use-angle=swiftshader` and `--in-process-gpu` were **not valid rendering
comparisons**: inspection of the actual Windows command lines showed those
switches absent, even though their environment variable was present. Do not
claim that those rendering modes were tested successfully or ruled out.
A Lightroom-specific WebView2 AdditionalBrowserArguments policy is under test.

The normal `run` command does not disable WebView2's sandbox. Explicit
`experiment-webview no-sandbox` is a development-only attempt, and the same
command-line verification is needed before interpreting its result.

The executable-name-specific policy was also ignored. The wildcard policy in
this dedicated prefix (modern and legacy loader locations, HKLM/HKCU) **did**
produce `--disable-gpu` in WebView2's Windows command line. With effective
software rendering, and then effective in-process GPU rendering, the window
remained white. GPU-sandbox-only relaxation also remained white. Default
sandbox settings were restored afterward.

DXVK 2.7.1 was downloaded from its official release, checksum-pinned and loaded
successfully in both Lightroom and WebView2. The same white window persisted.
WebView2 148.0.3967.70 from Microsoft's Update Catalog was staged separately
and its DLL load verified. Its window also remained white, with another GPU
fatal error. WebView2 153 remains installed.

With an effective `--no-sandbox` policy on 148, browser processes survived
long enough to expose a localhost DevTools target, but then failed with the
same GPU fatal error. A read-only DOM/screenshot request timed out. These
tests do not establish that page rendering works internally. The original
prefix was restored to sandboxed software rendering and its debug port removed.

Full GE-Proton11-6 (not just a Proton-derived Wine binary) was downloaded
with a pinned SHA-256 and run through UMU 1.4.4 inside Steam Runtime 4.
UMU verified the runtime archive checksum and platform mtree. This uses a
separate prefix copy under experiments/proton-ge. The first Xwayland launch
reached Lightroom and its sign-in window, which was visually still white.
Native Wayland rendering is under test. No login has been verified.

### Proton and Adobe CEF comparison

- Native Wayland under GE-Proton11-6 loaded winewayland.drv, but the sign-in
  surface stayed blank and was incorrectly oversized on the HiDPI display.
- On the next Proton Xwayland run, NGL timed out initializing WebView2 and
  selected its IE fallback. The user captured Adobe's "Update your browser"
  page. NGL's log and the EmbeddedWB window class confirm the fallback engine.
- Staged only ADC64/CEF64 and ADC64/NGL from the already verified official
  Creative Cloud archive. NGL detected both helper executables at the expected
  Common Files path and selected CEF:116.0.0.0:1.16.0.7.
- Adobe's helper logged CEF context and browser initialization. Its first
  Proton window was still blank; no sign-in success has been established.
- Restored WebView2 software policy, removing the temporary debugger and
  sandbox overrides. The CEF helper itself supplies --no-sandbox to its child
  processes; this was observed in its actual command lines.
- Wine Staging 11.17 is a separate runtime comparison; the package signature
  verified against the host Arch keyring. An optional Wine Mono setup prompt
  was closed, and prefix initialization repeated without installing Mono.

### Sign-in form rendered, approximately 23:10 CEST

Wine Staging 11.17 + DXVK 2.7.1 + the experimental Direct2D effect + genuine
Adobe CEF/NGL components displayed the complete Adobe sign-in form, including
email and social login choices. Verified both by an agent screenshot and the
user's live observation. The user is signing in; successful account return,
editing, export and sync must not be inferred from this page.

Active prefix: `experiments/wine-staging-11.17/prefix` under the application
data directory. Log: `20260915-230931-lightroom-debug.log`. Adobe's own helper
uses Chromium 116; its normal login form was accepted and rendered. The Adobe
helper's signature/payload was not modified. The desktop launcher now selects
this Wine Staging prefix. The running app was left untouched for user sign-in.

### Authentication milestone, approximately 23:12 CEST

The user completed genuine Adobe sign-in and confirmed successful return to
Lightroom. The native Lightroom main window remains open and the authentication
helper window closed. This establishes authenticated launch, not editing,
export accuracy, persistence, cloud sync, or complete application support.
The working instance was left running. No passwords or authentication tokens
are stored in the repository.
