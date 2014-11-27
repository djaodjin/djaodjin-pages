Introduction
============


Installation
------------

Dependencies
~~~~~~~~~~~~

Make sure to install these prerequisites packages prior to installation :

* Python >= 2.7
* Django >= 1.6
* Markdown>=2.4.1
* beautifulsoup4>=4.3.2
* djangorestframework>=2.4.2
* html5lib>=1.0
* pillow>=2.5.3

If you want to upload media files to S3, you will also need:

* boto>=2.32.1
* django-storages>=1.1.8
* django-celery>=3.1.16

Add the pages Django application to your INSTALLED_APPS in settings.py:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'pages',
        ...
    )
