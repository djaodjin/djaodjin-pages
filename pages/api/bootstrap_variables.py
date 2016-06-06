# Copyright (c) 2016, Djaodjin Inc.
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
#pylint: disable=no-member


from django.db import transaction
from rest_framework import generics, serializers, status
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response

from ..mixins import AccountMixin
from ..models import BootstrapVariable
from ..serializers import BootstrapVariableSerializer


class BootstrapVariableListAPIView(AccountMixin, generics.ListAPIView):

    serializer_class = BootstrapVariableSerializer

    def get_cssfile(self):
        cssfile = self.request.GET.get('cssfile', 'site.css')
        return cssfile

    def get_queryset(self):
        cssfile = self.request.GET.get('cssfile', 'site.css')
        queryset = BootstrapVariable.objects.filter(
            account=self.account, cssfile=self.get_cssfile())
        return queryset

    def put(self, request):
        serializer = self.serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            any_created = False
            for var in serializer.validated_data:
                obj, created = BootstrapVariable.objects.update_or_create(
                    account=self.account,
                    cssfile=self.get_cssfile(),
                    variable_name=var['variable_name'],
                    defaults={'variable_value': var['variable_value']})
                any_created |= created
        return Response(serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class BootstrapVariableDetail(AccountMixin, CreateModelMixin,
                              generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an bootstrap variable in a ``BootstrapVariable``.
    """
    lookup_field = 'variable_name'
    lookup_url_kwarg = 'variable_name'
    serializer_class = BootstrapVariableSerializer

    def get_cssfile(self):
        cssfile = self.request.GET.get('cssfile', 'site.css')
        return cssfile

    def get_queryset(self):
        return BootstrapVariable.objects.filter(
            account=self.account, cssfile=self.get_cssfile())

    def perform_create(self, serializer):
        serializer.save(account=self.account, cssfile=self.get_cssfile())
