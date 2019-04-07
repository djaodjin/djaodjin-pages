# Copyright (c) 2018, Djaodjin Inc.
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

from django.conf import settings
from django.conf.urls import include, url
from django.views.i18n import JavaScriptCatalog
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from pages.views.pages import PageView, EditView


urlpatterns = staticfiles_urlpatterns() \
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    url(r'jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'^app/$', PageView.as_view(template_name='index.html',
        body_bottom_template_name="pages/_body_bottom_edit_tools.html")),
    url(r'^$', PageView.as_view(template_name='index.html',
        body_bottom_template_name="pages/_body_bottom_edit_tools.html")),
    url(r'^', include('django.contrib.auth.urls')),
    url(r'^', include('pages.urls')),
    url(r'^content/', include('testsite.urls.content')),
    url(r'^edit(?P<page>\S+)?', EditView.as_view(), name='pages_edit'),
]
