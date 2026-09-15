# Contributing

The project is paused at the authentication milestone. Contributions and
reproducible results are welcome through issues and pull requests.

Start with [current status](docs/validation.md) and the
[issue tracker](https://github.com/LamplighterPaul/omarchy-lightroom-cc/issues).
Priorities are the main-window hang, Camera Raw GPU initialization, color
correctness and clean setup reproduction.

## Development

```sh
make check
```

`make check` compiles the Python launchers, syntax-checks the WebView2 capture
script and runs the unit tests. The automated tests cover launcher behavior and
payload handling. They do not run Adobe applications or prove compatibility.
Keep experiments isolated in separate prefixes and make changes reversible.
Explain the concrete failure, the change and the observed result; distinguish
hypotheses from verified fixes.

For reports, include Omarchy/desktop version, kernel, GPU/driver, Lightroom
version, runner, graphics backend and minimal reproduction steps. Share only
reviewed excerpts: Adobe logs, screenshots, crash dumps and Wine registry files
can expose credentials, account details or photos. Never attach an authenticated
prefix. Do not commit runtime archives or Adobe/Microsoft binaries.

Preserve upstream attribution and license notices. Original project contributions
use the MIT license; Wine-derived changes retain the applicable Wine license.
