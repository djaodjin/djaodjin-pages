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

"""
API URLs for sequence objects
"""

from ...api.sequences import (SequenceListCreateAPIView,
    SequenceRetrieveUpdateDestroyAPIView, LiveEventAttendanceAPIView,
    RemoveElementFromSequenceAPIView, AddElementToSequenceAPIView)

from ...compat import path

urlpatterns = [
    path('sequences',
         SequenceListCreateAPIView.as_view(),
         name='api_sequence_list_create'),
    path('sequences/<slug:sequence>',
         SequenceRetrieveUpdateDestroyAPIView.as_view(),
         name='api_sequence_retrieve_update_destroy'),

    path('sequences/<slug:sequence>/elements',
         AddElementToSequenceAPIView.as_view(),
         name='api_add_element_to_sequence'),
    path('sequences/<slug:sequence>/elements/<int:rank>',
         RemoveElementFromSequenceAPIView.as_view(),
         name='api_remove_element_from_sequence'),

    path('sequences/<slug:sequence>/<int:rank>/<username>/mark-attendance',
         LiveEventAttendanceAPIView.as_view(),
         name='api_mark_attendance')
]
