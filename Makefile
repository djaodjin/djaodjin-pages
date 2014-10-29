# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= .
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin

PYTHON        := $(binDir)/python
installDirs   ?= install -d

install::
	cd $(srcDir) && $(PYTHON) ./setup.py install --quiet

initdb:
	-rm -f db.sqlite3
	cd $(srcDir) && $(PYTHON) ./manage.py migrate --noinput
	cd $(srcDir) && $(PYTHON) ./manage.py loaddata \
						testsite/fixtures/initial_data.json

doc:
	$(installDirs) docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/docs
