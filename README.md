djaodjin-pages is a Django application that implements a Content Management
System (CMS) for practices sharing.

Major Features:

- Hierachical structure of content elements
- Text edition (optional: markdown syntax)
- Media gallery (drag'n'drop in markdown or media placeholder)

Development
===========

After cloning the repository, create a virtualenv environment, install
the prerequisites, create the database then run the testsite webapp.

<pre><code>
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install -r testsite/requirements.txt

    # Installs Javascript prerequisites to run in the browser
    $ make vendor-assets-prerequisites

    # Create the testsite database
    $ make initdb

    # Run the testsite server
    $ python manage.py runserver

    # Browse http://localhost:8000/

</code></pre>


Release Notes
=============

Tested with

- **Python:** 3.7, **Django:** 3.2 (legacy)
- **Python:** 3.10, **Django:** 4.2 ([LTS](https://www.djangoproject.com/download/))
- **Python:** 3.12, **Django:** 5.2 (latest)

0.8.6

  * sorts newsfeed most recent first
  * fixes using S3Storage with Django5

[previous release notes](changelog)

Version 0.4.3 is the last version that contains the HTML templates
online editor. This functionality was moved to [djaodjin-extended-templates](https://github.com/djaodjin/djaodjin-extended-templates/)
as of version 0.5.0.
