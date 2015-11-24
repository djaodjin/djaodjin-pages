# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= $(realpath .)
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin

PYTHON        := $(binDir)/python
installDirs   ?= install -d
installFiles  := install -p -m 644

ASSETS_DIR    := $(srcDir)/testsite/static/

install::
	cd $(srcDir) && $(PYTHON) ./setup.py --quiet \
		build -b $(CURDIR)/build install

initdb:
	-rm -rf testsite/media/pages
	-rm -f db.sqlite3
	cd $(srcDir) && $(PYTHON) ./manage.py migrate --noinput

doc:
	$(installDirs) docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/docs

bower-prerequisites: $(srcDir)/bower.json
	$(installFiles) $^ .
	bower install --verbose --config.cwd="$(PWD)"
	$(installDirs) -d $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor/fonts $(ASSETS_DIR)/vendor/css $(ASSETS_DIR)/vendor/js $(ASSETS_DIR)/vendor/js/ace
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
	$(installFiles) bower_components/requirejs/require.js $(ASSETS_DIR)/vendor/js
	$(installFiles) bower_components/angular/angular.js $(ASSETS_DIR)/vendor/js
	cp -r bower_components/ace/lib/ace/ $(ASSETS_DIR)/vendor/js/ace

