djaodjin-pages is a Django application that allow live templates edition
and upload templates packages.

Major Features:

- Text edition (optional: markdown syntax)
- Media gallery (drag'n'drop in markdown or media placeholder)
- Upload template packages

Tested with

- **Python:** 2.7, **Django:** 1.11.12 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.8.2
- **Python:** 3.6, **Django:** 1.11.12 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.8.2
- **Python:** 3.6, **Django:** 2.0.4 (latest),       **Django Rest Framework:** 3.8.2

Development
===========

After cloning the repository, create a virtualenv environment, install
the prerequisites, create the database then run the testsite webapp.

<pre><code>
    $ virtualenv <em>installTop</em>
    $ source <em>installTop</em>/bin/activate
    $ pip install -r testsite/requirements.txt
    $ make vendor-assets-prerequisites

    $ make initdb

    $ python manage.py runserver

    # Browse http://localhost:8000/
    # Start edit live templates
</code></pre>

Full documentation available soon at Read-the-Docs