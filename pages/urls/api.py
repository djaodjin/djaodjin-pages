# Copyright (c) 2015, Djaodjin Inc.
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

from django.conf.urls import patterns, url

from pages.api.edition import PageElementDetail, PagesElementListAPIView
from pages.api.upload_media import (
    upload_progress,
    MediaUpdateDestroyAPIView,
    MediaListAPIView)

from pages.api.upload_template import (
    UploadedTemplateListAPIView,
    UploadedTemplateAPIView)

urlpatterns = patterns('',
    url(r'^uploaded-media/get-progress/upload/',
        upload_progress),
    url(r'^uploaded-media/(?P<slug>[\w-]+)/',
        MediaUpdateDestroyAPIView.as_view(), name='media_element'),
    url(r'^uploaded-media/',
        MediaListAPIView.as_view(), name='uploaded_media_elements'),
    url(r'^editables/(?P<slug>[\w-]+)/',
        PageElementDetail.as_view(), name='edit_page_element'),
    url(r'^editables/',
        PagesElementListAPIView.as_view(), name='page_elements'),
    url(r'^uploaded-templates/(?P<pk>\d+)/',
        UploadedTemplateAPIView.as_view(),
        name='update_uploaded_template'),
    url(r'^uploaded-templates/',
        UploadedTemplateListAPIView.as_view(),
        name='get_uploadedtemplate_list'),
)
