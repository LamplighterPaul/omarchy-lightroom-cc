-- Load after Omarchy defaults from ~/.config/hypr/hyprland.lua.
-- Main Lightroom windows and Wine popup menus share this Proton app-id.
-- X11 override-redirect popups still receive Hyprland fades unless disabled.
o.window({ class = "steam_app_lightroomomarchyproton" }, {
  workspace = "10 silent",
  no_initial_focus = true,
  focus_on_activate = false,
  no_anim = true,
})
