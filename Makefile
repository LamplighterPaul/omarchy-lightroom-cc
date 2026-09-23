PREFIX ?= $(HOME)/.local

.PHONY: install check syntax

install:
	install -Dm755 bin/omarchy-lightroom-cc $(DESTDIR)$(PREFIX)/bin/omarchy-lightroom-cc
	install -Dm755 bin/lightroom-omarchy-proton $(DESTDIR)$(PREFIX)/bin/lightroom-omarchy-proton
	install -Dm644 manifest.json $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/manifest.json
	install -Dm644 config/performance-profile.json $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/performance-profile.json
	install -Dm644 diagnostics/webview-capture.mjs $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/tools/webview-capture.mjs
	install -Dm644 diagnostics/monitor.py $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/diagnostics/monitor.py
	install -Dm644 diagnostics/resources.py $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/diagnostics/resources.py
	install -Dm644 diagnostics/stall-trace.py $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/diagnostics/stall-trace.py
	install -Dm644 diagnostics/ui-scheduler.py $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/diagnostics/ui-scheduler.py

syntax:
	python3 -m py_compile bin/omarchy-lightroom-cc scripts/build-d2d1.py
	node --check diagnostics/webview-capture.mjs

check: syntax
	python3 -m unittest discover -s tests -v
