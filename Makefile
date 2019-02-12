# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= $(realpath .)
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin
CONFIG_DIR    ?= $(srcDir)
# XXX CONFIG_DIR should really be $(installTop)/etc/testsite
LOCALSTATEDIR ?= $(installTop)/var

NPM           ?= npm
PIP           := $(binDir)/pip
PYTHON        := TESTSITE_SETTINGS_LOCATION=$(CONFIG_DIR) $(binDir)/python
installDirs   ?= install -d
installFiles  := install -p -m 644

ASSETS_DIR    := $(srcDir)/testsite/static

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && $(PYTHON) manage.py migrate --help 2>/dev/null)),--run-syncdb,)

install::
	cd $(srcDir) && $(PYTHON) ./setup.py --quiet \
		build -b $(CURDIR)/build install

install-conf:: $(DESTDIR)$(CONFIG_DIR)/credentials \
                $(DESTDIR)$(CONFIG_DIR)/gunicorn.conf
	install -d $(DESTDIR)$(LOCALSTATEDIR)/db
	install -d $(DESTDIR)$(LOCALSTATEDIR)/run
	install -d $(DESTDIR)$(LOCALSTATEDIR)/log/gunicorn


$(DESTDIR)$(CONFIG_DIR)/credentials: $(srcDir)/testsite/etc/credentials
	install -d $(dir $@)
	[ -f $@ ] || \
		SECRET_KEY=`python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'` && sed \
		-e "s,\%(SECRET_KEY)s,$${SECRET_KEY}," $< > $@


$(DESTDIR)$(CONFIG_DIR)/gunicorn.conf: $(srcDir)/testsite/etc/gunicorn.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@


initdb: install-conf
	-cd $(srcDir) && rm -rf db.sqlite3 testsite-app.log testsite/media themes
	cd $(srcDir) && $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --noinput
	cd $(srcDir) && $(PYTHON) ./manage.py loaddata \
						testsite/fixtures/default-db.json
	cd $(srcDir) && $(installDirs) testsite/media
	cd $(srcDir) && $(installFiles) testsite/static/vendor/bootstrap.css testsite/media

doc:
	$(installDirs) docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/docs

clean:
	-rm -rf credentials gunicorn.conf db.sqlite3 testsite-app.log testsite/media themes

vendor-assets-prerequisites: $(srcDir)/package.json
	$(installFiles) $^ $(installTop)
	$(NPM) install --loglevel verbose --cache $(installTop)/.npm --tmp $(installTop)/tmp --prefix $(installTop)
	$(installDirs) -d $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor $(ASSETS_DIR)/img/bootstrap-colorpicker
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ace.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ext-language_tools.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ext-modelist.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ext-emmet.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/theme-monokai.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/mode-html.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/mode-css.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/mode-javascript.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/worker-html.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular/angular.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap/dist/css/bootstrap.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap/dist/css/bootstrap-theme.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap/dist/js/bootstrap.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/img/bootstrap-colorpicker/*.png $(ASSETS_DIR)/img/bootstrap-colorpicker
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/js/bootstrap-colorpicker.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	$(installFiles) $(installTop)/node_modules/jquery/dist/jquery.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery-ui-touch-punch/jquery.ui.touch-punch.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery.selection/dist/jquery.selection.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/pagedown/Markdown.Converter.js $(installTop)/node_modules/pagedown/Markdown.Sanitizer.js $(ASSETS_DIR)/vendor
	[ -f $(binDir)/lessc ] || (cd $(binDir) && ln -s ../node_modules/less/bin/lessc)
