PREFIX ?= $(HOME)/.local

.PHONY: install check syntax

install:
	install -Dm755 bin/omarchy-lightroom-cc $(DESTDIR)$(PREFIX)/bin/omarchy-lightroom-cc
	install -Dm644 manifest.json $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/manifest.json
	install -Dm644 diagnostics/webview-capture.mjs $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/tools/webview-capture.mjs

syntax:
	python3 -m py_compile bin/omarchy-lightroom-cc scripts/build-d2d1.py
	node --check diagnostics/webview-capture.mjs

check: syntax
	python3 -m unittest discover -s tests -v
