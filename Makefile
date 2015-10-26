# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= $(realpath .)
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin

PYTHON        := $(binDir)/python
installDirs   ?= install -d

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
	install $^ .
	bower install --verbose --config.cwd="$(PWD)"
	install -d $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor/fonts $(ASSETS_DIR)/vendor/css $(ASSETS_DIR)/vendor/js
	install bower_components/jquery/jquery.js $(ASSETS_DIR)/vendor/js
	install bower_components/jqueryui-touch-punch/jquery.ui.touch-punch.js $(ASSETS_DIR)/vendor/js
	install bower_components/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor/css
	install bower_components/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor/js
	install bower_components/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor/css
	install bower_components/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	install bower_components/font-awesome/fonts/* $(ASSETS_DIR)/vendor/fonts
	install bower_components/hallo/dist/hallo.js $(ASSETS_DIR)/vendor/js
	install bower_components/rangy-official/rangy-core.js $(ASSETS_DIR)/vendor/js
	install bower_components/jquery-ui/themes/base/jquery-ui.css $(ASSETS_DIR)/vendor/css
	install bower_components/jquery-ui/ui/jquery-ui.js $(ASSETS_DIR)/vendor/js
