Pages Edition
=============

Pages edition will allow you to edit live template and upload media.

Configuration
-------------

Add Pages settings to make it work properly:

.. code-block:: python

    # allow to save edition for an account
    # can be a user, organization...
    PAGES_ACCOUNT_MODEL = 'testsite.ExampleAccount'

    # allow to find the correct account on your url parameter
    PAGES_ACCOUNT_URL_KWARG = 'account_slug'


Usage
-----

To start with djaodjin-pages edition you need to replace your django TemplateView with PageView.

.. autoclass:: pages.views.PageView


Replace:

.. code-block:: python

    class HomeView(TemplateView):
        template_name = "index.html"

by:

.. code-block:: python

    class HomeView(PageView):
        template_name = "index.html"

Djaodjin-pages edition run thanks to djaodjin-editor jQuery plugin. So, you have now to work on your templates.
All templates you want to get live edtion need some modification

First include at the pages_edition.html in all templates or in your base.html of your project to make it available on each PageView

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
    <title>your templates</title>
    {% pages_static_css %}
    </head>
    <body>
        ....
        ....
        {% include "pages_edition.html" %}
        {% pages_static_js %}
    </body>
    </html>

Everywhere you want enable edition you have to add "editable" class on your html tag.
ex:
    
.. code-block:: html

    <h1 class="editable">Hello world!</h1>

Djaodjin-pages allows you two kind of edition.

- Simple edition: use it for header or little paragraph.
- Markdown edition: use it for big paragraph. It allows you to format your paragraph with subtitle, list...

By default "editable" class enable Simple edition of your html tag. If you want to enable Markdown edition you have to add "edit-markdown" class.

ex:

.. code-block:: html

    <p class="editable edit-markdown">Lorem ipsum dolor sit amet,
    consectetur adipisicing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
    quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
    cillum dolore eu fugiat nulla pariatur.</p>

