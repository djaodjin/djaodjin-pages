djaodjin-pages is a Django application that allow live templates edition and upload templates packages.

Major Features:

- Text edition (optional: markdown syntax)
- Media gallery (drag'n'drop in markdown or media placeholder)
- Upload template packages

Development
===========

After cloning the repository, create a virtualenv environment, install
the prerequisites, create the database then run the testsite webapp.

    $ virtualenv-2.7 _installTop_
    $ source _installTop_/bin/activate
    $ pip install -r requirements.txt -r testsite/requirements.txt
    $ python manage.py migrate
    $ python manage.py runserver

    # Browse http://localhost:8000/
    # Start edit live templates

Full documentation available soon at Read-the-Docs