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

#pylint: disable=no-init,no-member
#pylint: disable=old-style-class,maybe-no-member

from django.conf import settings
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework import generics
from rest_framework.response import Response

from pages.models import PageElement, UploadedImage
from pages.serializers import PageElementSerializer
from pages.mixins import AccountMixin


class PagesElementListAPIView(AccountMixin, generics.ListCreateAPIView):
    pass

class PageElementDetail(AccountMixin, CreateModelMixin,
                        generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an editable element on a ``PageElement``.
    """
    serializer_class = PageElementSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        kwargs = {self.lookup_field: self.kwargs.get(self.lookup_url_kwarg)}
        #pylint:disable=star-args
        return PageElement.objects.filter(
            account=self.get_account(), **kwargs)

    def perform_create(self, serializer):
        return serializer.save(
            slug=self.kwargs.get(self.lookup_url_kwarg),
            account=self.get_account())

    def update_or_create_pagelement(self, request, *args, **kwargs):
        #pylint: disable=unused-argument
        """
        Update or create a ``PageElement`` with a text overlay
        of the default text present in the HTML template.
        """

        queryset = self.get_queryset()
        if queryset.exists():
            self.object = queryset.get()
            serializer = self.get_serializer(self.object, data=request.data)
            serializer.is_valid(raise_exception=True)
            response_status = status.HTTP_200_OK
            self.perform_update(serializer)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.object = self.perform_create(serializer)
            response_status = status.HTTP_201_CREATED

        if self.object.slug.startswith('djmedia-'):
            text = request.DATA['text']
            #check S3 version exists
            if not 's3.amazon' in text:
                try:
                    upload_image = UploadedImage.objects.get(
                        uploaded_file_temp=text.replace('/media/', ''))
                    if upload_image.uploaded_file:
                        text = \
                            settings.S3_URL + '/' + text.replace('/media/', '')
                except: #pylint: disable=bare-except
                    pass

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=response_status, headers=headers)

    def put(self, request, *args, **kwargs):
        return self.update_or_create_pagelement(request, *args, **kwargs)
