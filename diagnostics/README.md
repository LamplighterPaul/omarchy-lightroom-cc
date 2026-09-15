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
