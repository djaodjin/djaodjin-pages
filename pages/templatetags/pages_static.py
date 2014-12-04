# Copyright (c) 2014, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django import template
from django.forms.widgets import Media

register = template.Library()

@register.simple_tag()
def pages_static_js():
    javascript = [
        "vendor/js/jquery.js",
        "vendor/js/bootstrap.js",
        "js/ajax_setup.js",
        "vendor/js/dropzone.js",
        "vendor/js/jquery.autosize.js",
        "vendor/js/jquery.selection.js",
        "vendor/js/Markdown.Converter.js",
        "vendor/js/Markdown.Sanitiser.js",
        "vendor/js/djaodjin-editor.js",
        "vendor/js/jquery-ui.js",
        "vendor/js/jquery.ui.touch-punch.js",
        "vendor/js/jquery.ui-contextmenu.js",
        "vendor/js/djaodjin-sidebar-gallery.js",
        "js/init_plugin.js"]
    media = Media(js=javascript)
    return media.render()


@register.simple_tag
def pages_static_css():
    stylesheets = {
        'screen': (
            "vendor/css/bootstrap.min.css",
            "vendor/css/jquery-ui.css",
            "vendor/css/djaodjin-editor.css",
            "vendor/css/djaodjin-sidebar-gallery.css")
        }

    media = Media(css=stylesheets)
    return media.render()
