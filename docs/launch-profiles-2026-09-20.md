# Tested launch profiles

The application now supports a persistent `performance` profile binding immutable
11.7-3-rc1 to photo retention and the MangoHud late limiter. The `stable` profile
selects the existing 11.7-2 runtime and DXVK limiter. No runtime directory is
renamed or modified by profile selection. Without a saved choice, stable remains
the default. On this machine performance has been selected for the next launch;
the already-running production Lightroom remains on stable.

The profile definition in `config/performance-profile.json` pins the version and
all 14 rebuilt component hashes. Selection and launch validate those files and
require the staged MangoHud layer. A failed validation leaves the saved choice
unchanged. The saved preference is atomically replaced in the application data
directory; no prefix, registry, photo or credential is edited by this operation.

`--profile stable|performance` overrides the saved choice for one command.
`--runtime NAME` bypasses named-profile defaults for experiments; combining the
two is rejected. User environment overrides for limiter/retention still work.
The desktop entry follows the saved choice by default, and explicit profile or
runtime arguments are retained when generating a pinned desktop entry.

```sh
lightroom-omarchy-proton use-profile performance
# After closing Lightroom normally:
lightroom-omarchy-proton stop
lightroom-omarchy-proton run
```

For rollback, close Lightroom, stop the prefix, then select `use-profile stable`.
The launcher never starts a new runtime over live processes from a different
runtime. `status` exposes `runtime_switch_pending`; this is true for the current
production session after selecting performance. It does not mean the current
process has been upgraded. A profile change does not close that process.

## Validation

- All 14 actual candidate component hashes matched the source definition.
- 33 launcher tests pass, covering modified component rejection, missing limiter,
  atomic preference preservation on failure, stable recovery, environment
  overrides and rejection of runtime mixing before configuration helpers run.
- The installed `--profile performance run` command used the normal silent
  desktop-dispatch path into the private X11 fixture. Its process mapped rc1,
  retained the signed-in library and displayed the photo at the existing 2× scale.
- Actual process environment contained `PROTON_VERB=run`, DXVK sync interval zero
  and cap zero, `fps_limit=120,fps_limit_method=late,no_display=1`, and photo
  retention enabled. No explicit limiter/retention environment override was
  supplied for that launch. The normal-launch screenshot showed no overlay.
- Real vertical dragging and File-menu open/close gestures completed; the app
  then quit normally. The production process remained live throughout.
- Saved performance and explicit stable `status` commands resolved the expected
  different runtime directories. Performance reported a pending production
  runtime switch; stable did not.

The earlier [packaged candidate tests](loupe-retention-2026-09-19.md),
[per-photo limiter comparison](photo-presentation-2026-09-19.md),
[mixed-photo checks](mixed-photo-2026-09-19.md) and
[observer overhead investigation](observer-cost-2026-09-19.md) provide the
performance and compatibility evidence. This makes the candidate repeatable and
ready to test; it does not establish sustained visible 120 FPS, native parity,
or remove the need to observe normal Hyprland use. User feedback on actual
photo dragging and menus has been requested after the next session switch.
