#Djaodjin-pages: Edition

*__Make your django TemplateView editable.__*

---

## Configuration
---

Install djaodjin-pages by adding ```pages``` in your ```INSTALLED_APP```.

``` python
    INSTALLED_APP = (
        ...
        'pages',
        ...
    )
```

If you want to allow edition of the same template by multiple account (User, Organization...) you need to configure djaodjin-pages ```ACCOUNT_MODEl```.

In your urls.py:

``` python
    urlpatterns = patterns('',
        ...
        url(r'^(?P<slug>[\w-]+)/', include('pages.urls')),
        ...
    )
```

In your settings.py

``` python
    PAGES = {
        'PAGES_ACCOUNT_MODEL' : 'yoursite.ExampleAccount'
        'PAGES_ACCOUNT_URL_KWARG' : 'account_slug'
    }
```
---

## Usage
---

### Django settings

To start with djaodjin-pages edition you need to replace your django TemplateView with Djaodjin-pages PageView.

Replace :

``` python
    class HomeView(TemplateView):
        template_name = "index.html"
```

by:

``` python
    from pages.views import PageView

    class HomeView(PageView):
        template_name = "index.html"
```

### Template settings

All templates you want to get live edtion need some modifications. Djaodjin-pages run with [Djaodjin-editor](http://djaodjin.com) jquery plugin.

All you need to add is a valid id on your editable section.

```html
<h1 class="editable" id="main-heading">Hello world!</h1>
```

Be careful to make ids unique.





