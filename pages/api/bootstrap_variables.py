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



import logging, os, shutil

from ..mixins import AccountMixin
from ..models import BootstrapVariable
from ..serializers import BootstrapVariableSerializer
from ..utils import validate_title
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import transaction
from django.http import Http404
from django.template import TemplateSyntaxError
from django.template.defaultfilters import slugify
from django.template.loader import get_template
from django.utils._os import safe_join
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import status, generics, serializers
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.response import Response


LOGGER = logging.getLogger(__name__)



class BootstrapVariableMixin(AccountMixin):

    pass


class BootstrapVariableListAPIView(AccountMixin,
                                   APIView):
    
    def get(self, request):
        serializer = BootstrapVariableSerializer(self.get_queryset(), many=True)
        
        return Response(serializer.data)
                        
    def put(self, request):
        
        print request.data

        
        with transaction.atomic():
            BootstrapVariable.objects.filter(account=self.account).delete()

            child_serializer = BootstrapVariableSerializer()            
            serializer = serializers.ListSerializer(data=request.data,child=child_serializer)
            serializer.is_valid()
            serializer.save(account=self.account)

            
            # serializer = BootstrapVariableSerializer(self.get_queryset(), many=True)
            return Response(serializer.data)

    

    def get_queryset(self):
        queryset = BootstrapVariable.objects.filter(account=self.account)
        return queryset

    # def perform_create(self, serializer):
    #     serializer.save(account=self.account)

    # def perform_update(self, serializer):
    #     serializer.save(account=self.account)


class BootstrapVariableDetail(BootstrapVariableMixin, CreateModelMixin,
                              generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an bootstrap variable in a ``BootstrapVariable``.
    """
    lookup_field = 'variable_name'
    lookup_url_kwarg = 'variable_name'
    serializer_class = BootstrapVariableSerializer

    def get_queryset(self):
        return BootstrapVariable.objects.filter(account=self.account)

    def perform_create(self, serializer):
        serializer.save(account=self.account)
