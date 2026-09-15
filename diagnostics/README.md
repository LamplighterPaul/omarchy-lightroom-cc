# Local diagnostics

`lightroom-ui.c` enumerates Lightroom's windows, reads only its WebView2 rendering
setting, and optionally clicks its native Sign In control. It does not read
browser URLs, password fields or account tokens. Compile with the development
MinGW toolchain into `$LRCC_DATA/tools/lightroom-ui.exe`; use the launcher's
`ui` or `ui click-sign-in` command. The environment reader assumes x86-64
Windows structure offsets and is a development diagnostic, not application code.

`browser-status` reports only known rendering flags for processes in this Wine
prefix. An empty list can mean the app has exited or the process namespace is
not visible. Do not infer successful flag propagation from it.

`capture-webview` uses Node's built-in WebSocket client to request DOM size
counts and screenshots from a temporarily enabled localhost WebView2 debugger.
It never logs complete navigation URLs, page text, cookies or browser storage.
Screenshots remain private local diagnostics under the data directory.

Rendering policies persist in the selected Wine prefix. Profiles containing
`diagnostic` expose localhost port 19223; `no-sandbox-test` and
`no-sandbox-diagnostic` disable Chromium sandboxing and are temporary development
tests. Stop the selected runner and apply `repair-webview-rendering software`
after these experiments to remove the debug port and restore sandboxing.

## Main-window hang

`ui responsiveness` sends `WM_NULL` with a two-second timeout. A timeout is
evidence that the window is not responding, not a diagnosis of the cause.
Wine may return immediately if it already considers the window hung.

`omarchy-lightroom-cc --runner staging native-debug` launches standalone Wine
as GDB's child, avoiding attach restrictions on systems with ptrace scope 1.
Run it in an interactive terminal; GDB must be installed. It passes Wine's
normal exception signals through and suppresses frame arguments by default.
Press Ctrl-C at the hang, then use `thread apply all bt` to inspect stacks.
Debugger output can still contain private paths or data; review before sharing.
This command does not currently support the full Proton runner.
