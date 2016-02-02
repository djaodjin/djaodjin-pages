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
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import MediaTag
from ..mixins import AccountMixin, UploadedImageMixin
from ..serializers import MediaItemListSerializer
from ..utils import validate_title


class MediaListAPIView(UploadedImageMixin, AccountMixin, GenericAPIView):

    serializer_class = MediaItemListSerializer
    pagination_class = PageNumberPagination

    def get(self, request, *args, **kwargs):
        tags = None
        search = self.request.GET.get('q')
        if search:
            validate_title(search)
            tags = MediaTag.objects.filter(tag__startswith=search)\
                .values_list('location', flat=True)
        queryset = self.list_media(
            self.get_default_storage(self.account), tags)
        # XXX - Deactivate pagination until not
        # implemented in djaodjin-sidebar-gallery
        # page = self.paginate_queryset(queryset['results'])
        # if page is not None:
        #     queryset = {'count': len(page), 'results' : page}
        return Response(queryset)

    def post(self, request, *args, **kwargs):
        #pylint: disable=unused-argument,too-many-locals
        uploaded_file = request.data['file']
        sha1 = hashlib.sha1(uploaded_file.read()).hexdigest()

        # Store filenames with forward slashes, even on Windows
        file_name = force_text(uploaded_file.name.replace('\\', '/'))
        sha1_filename = sha1 + os.path.splitext(file_name)[1]
        storage = self.get_default_storage(self.account)

        result = {}
        if storage.exists(sha1_filename):
            result = {
                "message": "%s is already in the gallery." % file_name}
            response_status = status.HTTP_200_OK
        else:
            storage.save(sha1_filename, uploaded_file)
            response_status = status.HTTP_201_CREATED
        result.update({
            'location': storage.url(sha1_filename),
            'tags': []
            })
        return Response(result, status=response_status)

    def delete(self, request, *args, **kwargs):
        """
        Delete media
        {
            items: [
                {location: "/media/item/url1.jpg"},
                {location: "/media/item/url2.jpg"},
                ....
            ]
        }
        """
        #pylint: disable=unused-argument
        storage = self.get_default_storage(self.account)
        serializer = MediaItemListSerializer(data=request.data)
        serializer.is_valid()
        validated_data = serializer.validated_data
        filter_list = self.build_filter_list(validated_data)
        list_delete_media = self.list_delete_media(storage, filter_list)
        if list_delete_media['count'] > 0:
            self.delete_media_items(storage, list_delete_media)
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        """
        Update media tag
        {
            items: [
                {location: "/media/item/url1.jpg"},
                {location: "/media/item/url2.jpg"},
                ....
            ],
            tags: ['tag1', 'tag2']
        }
        will apply tag1 and tag2 to both media location
        """
        #pylint: disable=unused-argument
        storage = self.get_default_storage(self.account)
        serializer = MediaItemListSerializer(data=request.data)
        serializer.is_valid()
        validated_data = serializer.validated_data
        filter_list = self.build_filter_list(validated_data)
        tags = validated_data.get('tags')

        list_media = self.list_media(storage, filter_list)
        if list_media['count'] > 0:
            self.update_media_tag(tags, list_media)
            return Response(list_media, status=status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
