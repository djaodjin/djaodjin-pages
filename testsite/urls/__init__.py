# Copyright (c) 2024, Djaodjin Inc.
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
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from pages.compat import include, path
from pages.api.elements import PageElementIndexAPIView
from pages.api.sequences import SequencesIndexAPIView

from ..views.app import IndexView

urlpatterns = staticfiles_urlpatterns() \
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path('', include('django.contrib.auth.urls')),
    path('app/supplier-1/',
        TemplateView.as_view(template_name='index.html')),
    path('app/energy-utility/',
        IndexView.as_view()),
    # Replaced
    # path('', include('pages.urls')),
    # by following to insert `account` into the path.
    path('api/editables/<slug:profile>/', include('pages.urls.api.editables')),
    path('api/attendance/<slug:profile>/', include('pages.urls.api.sequences')),
    path('api/progress/', include('pages.urls.api.progress')),
    path('api/content/', include('pages.urls.api.readers')),
    path('api/content/', include('pages.urls.api.noauth')),
    path('api/content', PageElementIndexAPIView.as_view(),
        name="api_content_index"),
    path('api/sequences', SequencesIndexAPIView.as_view(),
         name='api_sequences_index'),
    path('api/', include('pages.urls.api.assets')),
    path('', IndexView.as_view()),
    path('', include('pages.urls.views')),
]
