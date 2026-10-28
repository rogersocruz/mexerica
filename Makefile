# Mexerica — instalação
#   make install                      -> /usr/local (requer sudo)
#   make install PREFIX=$HOME/.local AUTOSTARTDIR=$HOME/.config/autostart
#   (o install.sh faz a instalação de usuário com os caminhos certos)

PREFIX       ?= /usr/local
DESTDIR      ?=
BINDIR       ?= $(PREFIX)/bin
DATADIR      ?= $(PREFIX)/share
PKGDATADIR   ?= $(DATADIR)/mexerica
AUTOSTARTDIR ?= /etc/xdg/autostart
UUID          = mexerica@rogersocruz.github.io
EXTDIR       ?= $(DATADIR)/gnome-shell/extensions/$(UUID)
# scripts do Nautilus são por usuário: só o install.sh passa a pasta
NAUTILUSDIR  ?=
NAUTILUS_SCRIPT = Converter com a Mexerica
APP_ID        = io.github.rogersocruz.Mexerica
PYTHON       ?= python3

SUBST = sed -e 's|@BINDIR@|$(BINDIR)|g' -e 's|@PKGDATADIR@|$(PKGDATADIR)|g'

.PHONY: install uninstall test check

install:
	install -d $(DESTDIR)$(PKGDATADIR)
	cp -r mexerica $(DESTDIR)$(PKGDATADIR)/
	find $(DESTDIR)$(PKGDATADIR) -name __pycache__ -prune -exec rm -rf {} +
	install -d $(DESTDIR)$(BINDIR)
	$(SUBST) bin/mexerica.in > $(DESTDIR)$(BINDIR)/mexerica
	chmod 755 $(DESTDIR)$(BINDIR)/mexerica
	install -d $(DESTDIR)$(DATADIR)/applications $(DESTDIR)$(DATADIR)/dbus-1/services
	$(SUBST) data/$(APP_ID).desktop > $(DESTDIR)$(DATADIR)/applications/$(APP_ID).desktop
	$(SUBST) data/$(APP_ID).service > $(DESTDIR)$(DATADIR)/dbus-1/services/$(APP_ID).service
	install -d $(DESTDIR)$(AUTOSTARTDIR)
	$(SUBST) data/$(APP_ID)-autostart.desktop > $(DESTDIR)$(AUTOSTARTDIR)/$(APP_ID).desktop
	install -Dm644 data/icons/$(APP_ID).svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP_ID).svg
	install -d $(DESTDIR)$(EXTDIR)
	install -m644 extension/$(UUID)/metadata.json extension/$(UUID)/extension.js $(DESTDIR)$(EXTDIR)/
	if [ -n "$(NAUTILUSDIR)" ]; then \
		install -d "$(DESTDIR)$(NAUTILUSDIR)" && \
		$(SUBST) data/nautilus-script.in > "$(DESTDIR)$(NAUTILUSDIR)/$(NAUTILUS_SCRIPT)" && \
		chmod 755 "$(DESTDIR)$(NAUTILUSDIR)/$(NAUTILUS_SCRIPT)"; \
	fi

uninstall:
	rm -rf $(DESTDIR)$(PKGDATADIR) $(DESTDIR)$(EXTDIR)
	rm -f $(DESTDIR)$(BINDIR)/mexerica \
	      $(DESTDIR)$(DATADIR)/applications/$(APP_ID).desktop \
	      $(DESTDIR)$(DATADIR)/dbus-1/services/$(APP_ID).service \
	      $(DESTDIR)$(AUTOSTARTDIR)/$(APP_ID).desktop \
	      $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP_ID).svg
	if [ -n "$(NAUTILUSDIR)" ]; then rm -f "$(DESTDIR)$(NAUTILUSDIR)/$(NAUTILUS_SCRIPT)"; fi

test:
	$(PYTHON) -m pytest -q tests
	node tests/extension_logic.test.mjs

check: test
