# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= $(realpath .)
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin

PYTHON        := $(binDir)/python
installDirs   ?= install -d
installFiles  := install -p -m 644

ASSETS_DIR    := $(srcDir)/testsite/static/

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && $(PYTHON) manage.py migrate --help 2>/dev/null)),--run-syncdb,)

install::
	cd $(srcDir) && $(PYTHON) ./setup.py --quiet \
		build -b $(CURDIR)/build install

install-conf:: credentials

credentials: $(srcDir)/testsite/etc/credentials
	[ -f $@ ] || \
		SECRET_KEY=`python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'` ; \
		sed -e "s,\%(SECRET_KEY)s,$${SECRET_KEY}," $< > $@

initdb: install-conf
	-rm -rf testsite/media/pages
	-rm -f db.sqlite3
	cd $(srcDir) && $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --noinput
	cd $(srcDir) && $(PYTHON) ./manage.py loaddata \
						testsite/fixtures/default-db.json

doc:
	$(installDirs) docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/docs

clean:
	rm credentials db.sqlite3

bower-prerequisites: $(srcDir)/bower.json
	$(installFiles) $^ .
	bower install --verbose --config.cwd="$(PWD)"
	$(installDirs) -d $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor/fonts $(ASSETS_DIR)/vendor/css $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/jquery/jquery.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/jqueryui-touch-punch/jquery.ui.touch-punch.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor/css
	$(installFiles) bower_components/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor/css
	$(installFiles) bower_components/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	$(installFiles) bower_components/font-awesome/fonts/* $(ASSETS_DIR)/vendor/fonts
	$(installFiles) bower_components/hallo/dist/hallo.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/rangy-official/rangy-core.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/jquery-ui/themes/base/jquery-ui.css $(ASSETS_DIR)/vendor/css
	$(installFiles) bower_components/jquery-ui/ui/jquery-ui.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/textarea-autosize/dist/jquery.textarea_autosize.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/jquery-selection/src/jquery.selection.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/ace.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/ext-language_tools.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/ext-modelist.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/ext-emmet.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/theme-monokai.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/mode-html.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/mode-css.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/ace-builds/src/mode-javascript.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/angular/angular.js $(ASSETS_DIR)/vendor/js

