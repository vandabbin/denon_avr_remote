AVREMOTE_PY = avremote.py
AVREMOTE = avremote

INSTALL = install
PREFIX = /usr/local/bin

.NOTPARALLEL:

.PHONY: all
all:

.PHONY: install
install:
	$(INSTALL) -Dm 0755 $(AVREMOTE_PY) $(DESTDIR)$(PREFIX)/$(AVREMOTE)

.PHONY: uninstall
uninstall:
	$(RM) $(DESTDIR)$(PREFIX)/$(AVREMOTE)

.PHONY: clean
clean:

