# Copyright (c) 2022, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''API URLs for the pages application'''

from django.conf.urls import url

from ...import settings
from ...api.elements import (PageElementEditableListAPIView,
    PageElementEditableDetail)
from ...api.relationship import (PageElementAliasAPIView,
    PageElementMirrorAPIView, PageElementMoveAPIView, RelationShipListAPIView)


urlpatterns = [
    url(r'^relationship',
        RelationShipListAPIView.as_view(), name='relationships'),
    url(r'^alias/(?P<path>%s)$' % settings.PATH_RE,
        PageElementAliasAPIView.as_view(), name='pages_api_alias_node'),
    url(r'^attach/(?P<path>%s)$' % settings.PATH_RE,
        PageElementMoveAPIView.as_view(), name='pages_api_move_node'),
    url(r'^mirror/(?P<path>%s)$' % settings.PATH_RE,
        PageElementMirrorAPIView.as_view(), name='pages_api_mirror_node'),
    url(r'^(?P<path>%s)$' % settings.NON_EMPTY_PATH_RE,
        PageElementEditableDetail.as_view(), name='pages_api_edit_element'),
    url(r'^$', PageElementEditableListAPIView.as_view(),
        name='pages_api_editables_index'),
]
