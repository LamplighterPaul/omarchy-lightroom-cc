PREFIX ?= $(HOME)/.local

.PHONY: install check
install:
	install -Dm755 bin/omarchy-lightroom-cc $(DESTDIR)$(PREFIX)/bin/omarchy-lightroom-cc
	install -Dm644 manifest.json $(DESTDIR)$(PREFIX)/share/omarchy-lightroom-cc/manifest.json

check:
	python3 -m unittest discover -s tests -v
