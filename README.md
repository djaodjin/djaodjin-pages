djaodjin-pages is a Django application that allow live templates edition
and upload templates packages.

Major Features:

- Text edition (optional: markdown syntax)
- Media gallery (drag'n'drop in markdown or media placeholder)
- Upload template packages

Tested with

- **Python:** 3.6, **Django:** 2.2 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.12
- **Python:** 3.6, **Django:** 3.2 (latest), **Django Rest Framework:** 3.12
- **Python:** 2.7, **Django:** 1.11 (legacy), **Django Rest Framework:** 3.9.4


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


Release Notes
=============

0.4.2

  * clears cache for Jinja2>=2.9

[previous release notes](changelog)
