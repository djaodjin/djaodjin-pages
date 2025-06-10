# Copyright (c) 2025, Djaodjin Inc.
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
import base64
import logging
import re
from io import BytesIO

import mammoth, requests
from bs4 import BeautifulSoup
from deployutils.helpers import datetime_or_now
from django.core.files.uploadedfile import (SimpleUploadedFile,
    TemporaryUploadedFile)
from django.db import transaction
from django.db.models import Max, Q
from django.http import Http404, QueryDict
from markdownify import markdownify as md
from rest_framework import (generics, response as api_response,
    status)
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import CreateModelMixin
from rest_framework.request import Request

from .. import settings
from ..docs import extend_schema
from ..compat import is_authenticated, reverse, gettext_lazy as _
from ..helpers import ContentCut, get_extra
from ..mixins import AccountMixin, PageElementMixin, TrailMixin
from ..models import (PageElement, RelationShip, build_content_tree,
    flatten_content_tree, Follow)
from ..serializers import (AssetSerializer, NodeElementCreateSerializer,
    PageElementDetailSerializer, PageElementTagSerializer)
from ..utils import validate_title
from .assets import process_upload

LOGGER = logging.getLogger(__name__)


class PageElementListMixin(TrailMixin):

    @property
    def visibility(self):
        return None

    @property
    def owners(self):
        return None

    def attach(self, elements):
        return elements

    def get_cut(self):
        cut_param = self.get_query_param('cut')
        return ContentCut(cut_param) if cut_param else None

    def get_results(self):
        if self.element:
            content_tree = build_content_tree(
                roots=[self.element], prefix=self.full_path,
                cut=self.get_cut(),
                visibility=self.visibility,
                accounts=self.owners)
            items = flatten_content_tree(
                content_tree, sort_by_key=False, depth=-1)
            items.pop(0)
        else:
            cut = self.get_cut()
            if not cut:
                cut = ContentCut()
            content_tree = build_content_tree(
                roots=None, prefix=self.full_path,
                cut=cut,
                visibility=self.visibility,
                accounts=self.owners)
            # We do not re-sort the roots such that member-only content
            # appears at the top.
            items = flatten_content_tree(content_tree, sort_by_key=False)

        results = []
        for item in items:
            searchable = get_extra(item, 'searchable', False)
            if searchable:
                results += [item]

        return results

    def get_queryset(self):
        results = self.get_results()
        self.attach(results)
        return results


class PageElementAPIView(PageElementListMixin, generics.ListAPIView):
    """
    Lists tree of page elements matching prefix

    Returns a flat list of page elements starting with a prefix. The `indent`
    field is used to indicate the level of the element in the tree.

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/boxes-and-enclosures HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 8,
          "next": null,
          "previous": null,
          "results": [
          {
            "slug": "metal",
            "path": null,
            "title": "Metal structures & equipment",
            "indent": 0
          },
          {
            "slug": "boxes-and-enclosures",
            "path": "/metal/boxes-and-enclosures",
            "title": "Boxes & enclosures",
            "indent": 1,
            "tags": [
              "industry",
              "pagebreak",
              "public",
              "scorecard"
            ]
          }
          ]
        }
    """
    serializer_class = PageElementDetailSerializer

    search_fields = (
        'title',
        'extra'
    )
    ordering_fields = (
        ('title', 'title'),
    )
    ordering = ('title',)

    filter_backends = (SearchFilter, OrderingFilter,)

    def list(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        results = self.get_queryset()

        # We have multiple roots so we create an unifying top-level root.
        element = self.element if self.element else PageElement()
        element.path = self.full_path
        element.results = results
        element.count = len(results)
        serializer = self.get_serializer(element)
        return api_response.Response(serializer.data)


class PageElementIndexAPIView(PageElementAPIView):
    """
    Lists tree of page elements

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 8,
          "next": null,
          "previous": null,
          "results": [
          {
            "slug": "metal",
            "path": null,
            "title": "Metal structures & equipment",
            "indent": 0
          },
          {
            "slug": "boxes-and-enclosures",
            "path": "/metal/boxes-and-enclosures",
            "title": "Boxes & enclosures",
            "indent": 1,
            "tags": [
              "industry",
              "pagebreak",
              "public",
              "scorecard"
            ]
          }
          ]
        }
    """

    @extend_schema(operation_id='content_index')
    def get(self, request, *args, **kwargs):
        return super(PageElementIndexAPIView, self).get(
            request, *args, **kwargs)


class PageElementSearchAPIView(PageElementAPIView):
    """
    Searches page elements

    Returns a list of page elements whose title matches a search criteria.

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/search HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [{
            "slug": "hello",
            "path": "/hello",
            "title": "Hello"
          }]
        }
    """

    @extend_schema(operation_id='content_search')
    def get(self, request, *args, **kwargs):
        return super(PageElementSearchAPIView, self).get(
            request, *args, **kwargs)

    def get_results(self):
        results = []
        for item in super(PageElementSearchAPIView, self).get_results():
            extra = item.get('extra', {})
            if extra:
                searchable = extra.get('searchable', False)
                if searchable:
                    results += [item]
        return results


class PageElementDetailAPIView(TrailMixin, generics.RetrieveAPIView):
    """
    Retrieves a page element

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/detail/adjust-air-fuel-ratio HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "adjust-air-fuel-ratio",
            "picture": null,
            "title": "Adjust air/fuel ratio",
            "text": "<h2>Background</h2><p>Some manufacturing processes may\
 involve heating operations.</p>",
            "extra": null
        }
    """
    serializer_class = PageElementDetailSerializer

    def get_object(self):
        return self.element

    def get(self, request, *args, **kwargs):
        if is_authenticated(self.request):
            # Marking the last time the PageElement was read by a user
            # following it
            try:
                follow_obj = Follow.objects.get(
                    user=self.request.user,
                    element=self.element)
                follow_obj.last_read_at = datetime_or_now()
                follow_obj.save()
            except Follow.DoesNotExist:
                pass

        return self.retrieve(request, *args, **kwargs)


class PageElementEditableListAPIView(AccountMixin, CreateModelMixin,
                                     PageElementAPIView):
    """
    Lists editable page elements

    This API endpoint lists page elements that are owned and thus editable
    by an account.

    **Tags**: editors

    **Examples

    .. code-block:: http

        GET /api/editables/alliance/content HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 5,
            "next": null,
            "previous": null,
            "results": [
                {
                    "path": null,
                    "title": "Construction",
                    "tags": ["public"],
                    "indent": 0
                },
                {
                    "path": null,
                    "title": "Governance & management",
                    "picture": "https://assets.tspproject.org/management.png",
                    "indent": 1
                },
                {
                    "path": "/construction/governance/the-assessment\
-process-is-rigorous",
                    "title": "The assessment process is rigorous",
                    "indent": 2,
                    "environmental_value": 1,
                    "business_value": 1,
                    "profitability": 1,
                    "implementation_ease": 1,
                    "avg_value": 1
                },
                {
                    "path": null,
                    "title": "Production",
                    "picture": "https://assets.tspproject.org/production.png",
                    "indent": 1
                },
                {
                    "path": "/construction/production/adjust-air-fuel\
-ratio",
                    "title": "Adjust Air fuel ratio",
                    "indent": 2,
                    "environmental_value": 2,
                    "business_value": 2,
                    "profitability": 2,
                    "implementation_ease": 2,
                    "avg_value": 2
                }
            ]
        }
    """
    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return NodeElementCreateSerializer
        return super(PageElementEditableListAPIView,
            self).get_serializer_class()


    def get_results(self):
        """
        Returns a list of heading and best practices
        """
        queryset = PageElement.objects.all()
        if self.account_url_kwarg in self.kwargs:
            queryset = PageElement.objects.filter(account=self.account)
        if self.path:
            queryset = queryset.filter(question__path__startswith=self.path)
        try:
            search_string = self.request.query_params.get('q', None)
            if search_string is not None:
                validate_title(search_string)
                queryset = queryset.filter(
                    Q(extra__icontains=search_string)
                    | Q(title__icontains=search_string))
        except ValidationError:
            pass
        return queryset


    @extend_schema(operation_id='editables_content_create')
    def post(self, request, *args, **kwargs):
        """
        Creates a page element

        **Tags: editors

        **Example

        .. code-block:: http

            POST /api/editables/alliance/content HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "title": "Boxes enclosures"
            }

        """
        #pylint:disable=useless-super-delegation
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(account=self.account)


class PageElementEditableDetail(AccountMixin, TrailMixin, CreateModelMixin,
                                generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves an editable page element

    **Tags: editors

    **Example

    .. code-block:: http

        GET /api/editables/alliance/content/boxes-enclosures HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "boxes-enclosures",
            "path": "/boxes-enclosures",
            "text": "Hello"
        }
    """
    serializer_class = PageElementDetailSerializer

    def get_object(self):
        self.element.results = self.element.get_relationships()
        return self.element

    def delete(self, request, *args, **kwargs):
        """
        Deletes a page element

        **Tags: editors

        **Example

        .. code-block:: http

            DELETE /api/editables/alliance/content/boxes-enclosures HTTP/1.1
        """
        #pylint:disable=useless-super-delegation
        return super(PageElementEditableDetail, self).delete(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Creates a page element under a prefix

        **Tags: editors

        **Example

        .. code-block:: http

            POST /api/editables/alliance/content/boxes-enclosures HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "text": "Hello"
            }

        """
        #pylint:disable=useless-super-delegation
        return super(PageElementEditableDetail, self).create(
            request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates a page element

        **Tags: editors

        **Example

        .. code-block:: http

            PUT /api/editables/alliance/content/boxes-enclosures HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes and enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "text": "Hello"
            }
        """
        #pylint:disable=useless-super-delegation
        return super(PageElementEditableDetail, self).put(
            request, *args, **kwargs)

    def perform_create(self, serializer):
        with transaction.atomic():
            element = serializer.save(account=self.account)

            # Attach the element in the content DAG
            parent = self.element
            rank = RelationShip.objects.filter(
                orig_element=parent).aggregate(Max('rank')).get(
                'rank__max', None)
            rank = 0 if rank is None else rank + 1
            RelationShip.objects.create(
                orig_element=parent, dest_element=element, rank=rank)

    def get_success_headers(self, data):
        path = data.get('path')
        if path:
            return {'Location': reverse('pages_editables_element', args=(
                self.element.account,
                path.strip(self.URL_PATH_SEP) + self.URL_PATH_SEP))}
        return {}

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            try:
                _ = self.element
                return super(PageElementEditableDetail, self).update(
                    request, *args, **kwargs)
            except Http404:
                pass
            return super(PageElementEditableDetail, self).create(
                request, *args, **kwargs)


class PageElementAddTags(AccountMixin, PageElementMixin,
                         generics.UpdateAPIView):
    """
    Adds tags to an editable node

    Add tags to a ``PageElement`` if they are not already present.

    **Example

    .. code-block:: http

        PUT /api/editables/alliance/content/boxes-and-enclosures/add-tags HTTP/1.1

    .. code-block:: json

        {
          "tag": "sometag"
        }

    responds

    .. code-block:: json

        {
        }
    """
    serializer_class = PageElementTagSerializer

    def get_object(self):
        return self.element

    def perform_update(self, serializer):
        curr_tags = serializer.instance.extra
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        add_tags = serializer.validated_data['tag'].split(',')
        for tag in add_tags:
            if not tag in curr_tags:
                curr_tags.append(tag)
        serializer.instance.extra = ','.join(curr_tags)
        serializer.instance.save()


class PageElementRemoveTags(AccountMixin, PageElementMixin,
                            generics.UpdateAPIView):
    """
    Remove tags from an editable node

    Remove tags from a ``PageElement``.

    **Examples

    .. code-block:: http

        PUT /api/editables/alliance/content/boxes-and-enclosures/remove-tags HTTP/1.1

    .. code-block:: json

        {
          "tag": "sometag"
        }

    responds

    **Examples

    .. code-block:: json

        {
        }
    """
    serializer_class = PageElementTagSerializer

    def get_object(self):
        return self.element

    def perform_update(self, serializer):
        curr_tags = serializer.instance.extra
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        remove_tags = serializer.validated_data['tag'].split(',')
        for tag in remove_tags:
            if tag in curr_tags:
                curr_tags.remove(tag)
        serializer.instance.extra = ','.join(curr_tags)
        serializer.instance.save()


class ImportDocxView(AccountMixin, PageElementMixin, generics.GenericAPIView):
    """
    Imports a .docx file's content into a PageElement's
    text field.

    **Tags**: editors

    **Example

    .. code-block:: http

        POST /api/editables/alliance/content/boxes-and-enclosures/import HTTP/1.1

    .. code-block:: json

        {
            "docx_location": "http://example.com/document.docx",
            "content_format": "MD"
        }

    responds

    .. code-block:: json

        {
            "slug": "boxes-enclosures",
            "text": "Hello"
        }
    """
    schema = None # XXX currently disabled in API documentation
    serializer_class = PageElementDetailSerializer

    def upload_image(self, request):
        """
        Upload an image and return its URL.
        """
        store_hash = True
        replace_stored = False
        content_type = None

        location = request.data.get("location", None)
        is_public_asset = request.query_params.get('public', False)

        response_data, response_status = process_upload(
            request, self.account, location, is_public_asset,
            store_hash, replace_stored, content_type)
        if response_status not in [200, 201]:
            raise ValidationError({'detail': _("error uploading asset")})

        return AssetSerializer().to_representation(response_data)['location']

    def process_image(self, img_tag, original_request):
        """
        Handle processing and uploading of an image in an HTML string.
        """
        image_data = img_tag["src"]
        if not image_data.startswith("data:image"):
            return None

        img_info, encoded = image_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        content_type = img_info.split(";")[0].split(":")[1]

        image_stream = SimpleUploadedFile("image.jpg", image_bytes,
            content_type)

        # Make a mutable copy of the request data
        if isinstance(original_request.data, QueryDict):
            mutable_data = original_request.data.copy()
        else:
            mutable_data = original_request.data

        mutable_data['file'] = image_stream

        # Create a new request object with the modified data
        #pylint:disable=protected-access
        new_request = Request(original_request._request,
            parsers=original_request.parsers)
        new_request._full_data = mutable_data
        new_request._data = mutable_data
        new_request._files = original_request._files
        new_request._user = original_request.user
        new_request._auth = original_request.auth

        # Skipping attributes that may not exist
        if hasattr(original_request, 'authenticator'):
            new_request._authenticator = original_request.authenticator

        return self.upload_image(new_request)


    def extract_and_upload_images(self, html, original_request):
        """
        Extract and upload images in the given HTML string.
        """
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            new_image_url = self.process_image(img, original_request)
            if new_image_url:
                img["src"] = new_image_url

        return str(soup)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        docx_location = serializer.validated_data.get("docx_location")
        content_format = serializer.validated_data.get("content_format", "MD")

        page_element = self.element
        if not page_element:
            return api_response.Response({'detail': 'Page Element not found'})
        if isinstance(docx_location, TemporaryUploadedFile):
            docx_content = docx_location
        elif docx_location.startswith(("http://", "https://", "www.")):
            response = requests.get(self.format_drive_url(docx_location),
                timeout=settings.HTTP_REQUESTS_TIMEOUT,
                stream=True)
            docx_content = BytesIO(response.content)
        else:
            with open(docx_location, "rb") as docx_file:
                docx_content = BytesIO(docx_file.read())

        # Convert .docx content to HTML
        result = mammoth.convert_to_html(docx_content)
        docx_content.close()
        html = result.value

        html = self.extract_and_upload_images(html, request)

        # If required, convert HTML to markdown format
        if content_format == "MD":
            html = md(html, extras="tables")
            page_element.content_format = 'MD'
        else:
            page_element.content_format = 'HTML'
        page_element.text = html
        page_element.save()

        return api_response.Response(
            {"detail": "Page element updated successfully"},
            status=status.HTTP_200_OK)

    @staticmethod
    def format_drive_url(url):
        """
        Formats a Google Docs' URL.
        """
        if "docs.google.com/document" not in url:
            raise ValueError("Invalid Google Docs URL: \"%s\"" % str(url))

        match = re.search(r"/d/([0-9A-Za-z_-]+)/", url)
        if not match:
            raise ValueError(
                "Could not extract document ID from URL: \"%s\"" % str(url))
        return ("https://docs.google.com/document/d/%s/export?format=docx" %
            str(match.group(1)))
