# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= $(realpath .)
installTop    ?= $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),$(abspath $(srcDir))/.venv)
binDir        ?= $(installTop)/bin
libDir        ?= $(installTop)/lib
CONFIG_DIR    ?= $(installTop)/etc/testsite
RUN_DIR       ?= $(abspath $(srcDir))

installDirs   ?= install -d
installFiles  := install -p -m 644
NPM           ?= npm
PIP           := pip
PYTHON        := python
TWINE         := twine


ASSETS_DIR    := $(srcDir)/htdocs/static
DB_NAME       ?= $(RUN_DIR)/db.sqlite

MANAGE        := TESTSITE_SETTINGS_LOCATION=$(CONFIG_DIR) RUN_DIR=$(RUN_DIR) $(PYTHON) manage.py

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && $(MANAGE) migrate --help 2>/dev/null)),--run-syncdb,)


install::
	cd $(srcDir) && $(PIP) install .


install-conf:: $(DESTDIR)$(CONFIG_DIR)/credentials \
                $(DESTDIR)$(CONFIG_DIR)/gunicorn.conf


dist::
	$(PYTHON) -m build
	$(TWINE) check dist/*
	$(TWINE) upload dist/*


build-assets: vendor-assets-prerequisites


clean:: clean-dbs
	[ ! -f $(srcDir)/package-lock.json ] || rm $(srcDir)/package-lock.json
	find $(srcDir) -name '__pycache__' -exec rm -rf {} +
	find $(srcDir) -name '*~' -exec rm -rf {} +

clean-dbs:
	[ ! -f $(DB_NAME) ] || rm $(DB_NAME)


doc:
	$(installDirs) build/docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/build/docs


initdb: clean-dbs
	$(installDirs) $(dir $(DB_NAME))
	cd $(srcDir) && $(MANAGE) migrate $(RUNSYNCDB) --noinput
	cd $(srcDir) && $(MANAGE) loaddata \
		testsite/fixtures/default-db.json


vendor-assets-prerequisites: $(installTop)/.npm/djaodjin-pages-packages


$(DESTDIR)$(CONFIG_DIR)/credentials: $(srcDir)/testsite/etc/credentials
	$(installDirs) $(dir $@)
	[ -f $@ ] || \
		sed -e "s,\%(SECRET_KEY)s,`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," $< > $@


$(DESTDIR)$(CONFIG_DIR)/gunicorn.conf: $(srcDir)/testsite/etc/gunicorn.conf
	$(installDirs) $(dir $@)
	[ -f $@ ] || sed -e 's,%(RUN_DIR)s,$(RUN_DIR),' $< > $@


$(installTop)/.npm/djaodjin-pages-packages: $(srcDir)/testsite/package.json
	$(installFiles) $^ $(installTop)
	$(NPM) install --loglevel verbose --cache $(installTop)/.npm --prefix $(installTop)
	$(installDirs) $(ASSETS_DIR)/vendor $(ASSETS_DIR)/fonts
	$(installFiles) $(installTop)/node_modules/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	$(installFiles) $(installTop)/node_modules/hallo/dist/hallo.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery/dist/jquery.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery.selection/dist/jquery.selection.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/pagedown/Markdown.Converter.js $(installTop)/node_modules/pagedown/Markdown.Sanitizer.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/rangy/lib/rangy-core.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/textarea-autosize/dist/jquery.textarea_autosize.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/vue/dist/vue.js $(ASSETS_DIR)/vendor
	touch $@


-include $(buildTop)/share/dws/suffix.mk

.PHONY: all check dist doc install build-assets vendor-assets-prerequisites
