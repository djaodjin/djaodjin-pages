Pages upload templates
======================

This feature will allow you to upload your templates package directly and make them live immediately

Configuration
-------------

.. code-block:: python
    

    # Path where you want to upload your templates
    PAGES_UPLOADED_TEMPLATE_DIR = BASE_DIR + '/testsite/templates'

    # Path where you want to upload static (js, css, img)
    PAGES_UPLOADED_STATIC_DIR = STATIC_ROOT


If you want to use djaodjin-pages features on your own templates you have to load some static.

{% pages_static_css %}

<link href="{% static 'example/test/css/custom.css' %}" rel="stylesheet"/>



{% include 'pages_edition.html' %}
{% pages_static_js %}