
from django import template
from django.forms.widgets import Media

register = template.Library()

@register.simple_tag
def pages_static_js():
    javascript = [
        "vendor/js/jquery.js",
        "js/ajax_setup.js",
        "vendor/js/dropzone.js",
        "vendor/js/jquery.autosize.js",
        "vendor/js/jquery.selection.js",
        "vendor/js/Markdown.Converter.js",
        "vendor/js/Markdown.Sanitiser.js",
        "vendor/js/djaodjin-editor.js",
        "vendor/js/jquery-ui.js",
        "vendor/js/jquery.ui.touch-punch.js",
        "vendor/js/djaodjin-sidebar-gallery.js",
        "js/init_plugin.js"]
        
    media = Media(js=javascript)
    return media.render()

@register.simple_tag
def pages_static_css():
    stylesheets = {
        'screen': ("vendor/css/bootstrap.min.css",
                "vendor/css/djaodjin-editor.css",
                "vendor/css/djaodjin-sidebar-gallery.css")
        }
        
    media = Media(css=stylesheets)
    return media.render()

@register.simple_tag
def pages_static_init(csrf, template_path, url_editor, url_gallery):
    print csrf
    html = '<input id="template_path" name="template_path" type="hidden" value="'+ str(template_path) +'"/>\
  <input id="url_editor" name="url_editor" type="hidden" value="'+ url_editor +'"/>\
  <input id="url_gallery" name="url_gallery" type="hidden" value="'+ url_gallery +'"/>\
  <input id="csrf_token" name="csrf_token" type="hidden" value="'+ str(csrf) +'"/>"'
    return unicode(html)