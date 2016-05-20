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


import hashlib, os

from django.utils.encoding import force_text
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import SiteCss
from ..mixins import AccountMixin, UploadedImageMixin
from ..serializers import SiteCssSerializer
from ..utils import validate_title

import cStringIO


class SiteCssAPIView(UploadedImageMixin, AccountMixin, APIView):

    def get(self, request, *args, **kwargs):
        try:
            css = SiteCss.objects.get(account=self.account)

            serializer = SiteCssSerializer(css)

            data = serializer.data
        except SiteCss.DoesNotExist:
            data = None


        return Response(data)




    def post(self, request, *args, **kwargs):

        uploaded_file = request.body
        sha1 = hashlib.sha1(uploaded_file).hexdigest()

        storage = self.get_default_storage(self.account)

        actual_name = storage.save('site.css', cStringIO.StringIO(uploaded_file))

        css,_ = SiteCss.objects.update_or_create(
            account=self.account,
            defaults={'url': storage.url(actual_name)}
        )
        serializer = SiteCssSerializer(css)

        return Response(serializer.data)


