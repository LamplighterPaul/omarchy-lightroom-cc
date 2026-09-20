# omarchy-lightroom-cc

Adobe **Lightroom CC (cloud)** on Omarchy, with a dedicated Proton runtime,
desktop integration and tools for measuring compatibility and performance.
Created by [Paul Zammit](https://github.com/LamplighterPaul).

This repository contains the **launcher, setup tooling, diagnostics and test
reports**. The companion [lightroom-omarchy-proton](https://github.com/LamplighterPaul/lightroom-omarchy-proton)
repository contains the **runtime patches, build recipes and pinned components**.

## Current status

**20 September 2026 — working developer preview with substantial improvements
to photo interaction, responsiveness and crash recovery.** The tested setup is
Lightroom 9.5.1 with custom Proton **11.7-3-rc2**, selected by the launcher's
`performance` profile. It runs through UMU and Steam Runtime 4; Steam itself is
not required. Proton supplies the Wine compatibility layer and graphics stack.

The signed-in cloud library loads, photos open, basic editing has been confirmed
by the operator, and sign-in survives normal restarts. The Intel GPU initializes
successfully and Lightroom reports automatic full acceleration. Desktop scaling
follows the monitor's scale (tested at 2x). Windows menus use the current Omarchy
palette, with centered entries and spacing; Adobe's own interface is retained.

### Measured progress

| Area | Result on the development machine |
| --- | --- |
| Black flashes while dragging | Greatly reduced by retaining the presented photo during background repaints. A controlled comparison recorded 112 blank samples out of 280 with retention disabled and zero with it enabled. [Evidence](docs/loupe-retention-2026-09-19.md). |
| Zoom | Disabling the transition animation reduced median time to a settled zoom image from 343 ms to 155–162 ms in repeated captures. [Evidence](docs/transitions-2026-09-20.md). |
| Menus | A targeted UI-thread scheduling hint reduced measured keyboard-menu opening time by about 30%, while keeping all CPU cores available to workers. Long outliers remain. [Evidence](docs/ui-scheduling-2026-09-20.md). |
| Sustained panning | Four controlled recordings had median renderer intervals around 8.33 ms; one retained stalls up to 25 ms. Physical-display 120 FPS and native performance parity remain unproven. [Evidence](docs/frame-telemetry-2026-09-20.md). |
| Stability | Normal close/restart works after shutdown fixes. Rc2 recovers from the stale display-controller query that caused a fatal X11 exit; Lightroom survived eight injected failures and subsequent interactions. Real sleep/wake validation remains. [Evidence](docs/randr-recovery-2026-09-20.md). |

These are measurements from one development machine, mostly using an isolated
display. Capture adds overhead, and results vary with the workload. Residual
stutters and photo-loading delays still need work; this is not a claim that all
flicker, stalls or crashes are gone.

## What still needs proving

- **Local file import and export:** neither workflow has been validated end to
  end. Opening existing cloud photos does not establish local-file support.
- **Colour accuracy:** ICC profiles, display transforms, gamut handling, soft
  proofing and exported colour fidelity remain unverified. The current
  experimental Direct2D colour-management effect is a pass-through, not a
  correct colour transform. Professional colour work is not validated.
- **Editing and sync:** basic edits work in observed use; complete tool coverage,
  saved-edit persistence and cloud upload consistency remain unverified.
- **Fresh installation and sign-in:** the working Proton environment was
  migrated from an authenticated prefix. A clean Proton-only setup and sign-in
  have not been reproduced end to end.
- **Broader stability:** real suspend/resume, display changes, long sessions and
  other hardware still need coverage. Photo changes measured around half a
  second typically, with longer outliers.
- **Runtime size:** the package still contains the full GE-Proton distribution
  with selected rebuilt components. A smaller Lightroom-specific runtime is
  future work; unnecessary components and their footprint have not yet been
  systematically audited or removed.

## Development and testing

A genuine Adobe subscription and interactive authentication are required. The
project is an independent developer preview, unsupported by Adobe.

```sh
git clone https://github.com/LamplighterPaul/omarchy-lightroom-cc.git
cd omarchy-lightroom-cc
make check
make install
```

`make install` installs the launcher and tooling. It does **not** provision a
complete Lightroom environment. Start with the companion runtime's
[build and packaging guide](https://github.com/LamplighterPaul/lightroom-omarchy-proton/blob/omarchy/omarchy/README.md).
The [earlier setup notes](docs/setup.md) document the incremental Wine-based
bootstrap and authentication route; they are historical context, not a verified
clean Proton installer.

For an already prepared environment with rc2 and MangoHud staged, close
Lightroom normally and stop its existing prefix before switching profiles:

```sh
lightroom-omarchy-proton stop
lightroom-omarchy-proton use-profile performance
lightroom-omarchy-proton run
```

The performance profile checks all 14 pinned component hashes. The older
`stable` profile is retained as a baseline; that name is not a guarantee of
complete workflow validation. Fresh installations default to that older profile
until another is selected. The desktop shortcut follows the saved profile.

Use `status` to inspect the selected runtime, `measure 30` to record CPU/GPU and
memory data, or `run-perf` instead of `run` to launch with the overlay. See the
[performance test loop](docs/performance-loop.md) and
[diagnostic tools](diagnostics/README.md). The
[scheduling](docs/ui-scheduling-2026-09-20.md) and
[zoom](docs/transitions-2026-09-20.md) reports document comparison and restore
options. Dated reports describe the builds tested at the time.

The current development launch convention uses **Super+0 (workspace 10)**
silently, so testing does not interrupt the desktop. This is a debugging
convention, not a Lightroom feature or a requirement of Proton.

Contributions should include reproducible steps and measured results. See
[CONTRIBUTING.md](CONTRIBUTING.md) and the
[issue tracker](https://github.com/LamplighterPaul/omarchy-lightroom-cc/issues).

## Credits and licensing

Original launcher, diagnostics and documentation: copyright © 2026 Paul Zammit
and contributors, [MIT](LICENSE). Wine-derived components retain their own
licenses. Thanks to Wine, GE-Proton, Valve Proton, UMU, DXVK, vkd3d-proton,
MangoHud, Omarchy, 6im0n and sander110419; see [THIRD_PARTY.md](THIRD_PARTY.md)
for attribution and license details.

Adobe binaries, credentials, photos and authenticated prefixes are not included
in this source repository. Adobe and Lightroom are trademarks of Adobe Inc.
