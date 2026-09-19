# Lightroom menu animation on the desktop

The private Weston test does not reproduce Hyprland's configured window fades.
Its five measured File-menu openings had a 6.531 ms median Lightroom initialization
callback and individual Wine layout/show/paint phases below 2 ms. Those timings
do not include input queues or the compositor's transition to fully visible pixels.

The running desktop is Hyprland 0.56.2, commit
`efb50993780079460b0cbed1363e2166a2de1d9f`. Its effective `fadeIn` setting was
enabled at speed 1.73 and `fadeOut` at 1.46. Hyprland documents animation speed
in [100 ms units](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Animations/),
so these configure 173 ms and 146 ms transitions respectively. This is not a
measurement of input latency: a fading menu can become partly visible sooner.

An Edit menu opened in the isolated Lightroom session produced this X11 window:

```text
class=steam_app_lightroomomarchyproton
override_redirect=1
geometry=445x819+1265+57
```

The main window has the same class and `override_redirect=0`. No desktop input
or production menu operation was used to inspect the popup. Inspection of the
[running Hyprland version's window animation code](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/desktop/view/animationControllers/WindowAnimationController.cpp)
shows that X11 borderless/override-redirect windows skip movement animation but
still initialize an opacity transition from zero to one. The
[animation manager](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/animation/AnimationManager.cpp)
honors the window's `no_anim` rule when updating those variables. This identifies
a desktop transition missing from the private test, and a plausible contributor
to the reported sluggish menu appearance.

## Applied change

The Lightroom-only rule now sets `no_anim = true`, alongside its existing
workspace 10, no-initial-focus and no-focus-on-activation settings. A reusable
snippet is in [config/lightroom-hyprland.lua](../config/lightroom-hyprland.lua).
Other applications retain their animations. The change uses the current
[documented window-rule syntax](https://wiki.hypr.land/Configuring/Basics/Window-Rules/).

The user's config was backed up before editing. `hyprctl reload` succeeded and
`hyprctl configerrors` was empty. Querying the existing production Lightroom
window with `hyprctl getprop address:... no_anim` changed from `false` to `true`.
The active window and workspace remained unchanged. Lightroom was not restarted,
and the rule applies to its future matching popup windows.

This removes the configured compositor transition for Lightroom, including the
current stable runtime. It is not evidence that every menu stall is fixed, nor
an end-to-end latency benchmark. The user's desktop comparison and remaining
input/render queue delays still need observation. The separate Proton photo
retention candidate and its component hashes are unchanged.

## Input-to-X11 mapping check

A read-only X11 listener on the private display timestamped `MapNotify` events
for matching override-redirect windows. Five File-menu mouse clicks produced
471×546 popups at the same position. Input submission to event receipt took
22.350, 27.357, 8.864, 11.013 and 8.118 ms. Input and event timestamps use the
same host monotonic clock; the input interval starts immediately before the
helper's coordinate lookup and XTest submission. Event receipt also includes
the observer's scheduling delay. No pixel readback ran during this check.

This small sample covers more of the input path than the callback timers, but
X11 mapping still precedes final visible pixels. It cannot prove desktop
input-to-display latency or exclude occasional long stalls. The observer source
is [x11-menu-events.c](../diagnostics/x11-menu-events.c), and the inputs, events
and matches are in [the numeric artifacts](measurements/20260919-menu-desktop/).
