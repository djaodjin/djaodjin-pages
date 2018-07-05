# Copyright (c) 2018, Djaodjin Inc.
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

import logging, zipfile

from rest_framework import parsers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ..mixins import ThemePackageMixin
from ..serializers import ThemePackageSerializer
from ..themes import install_theme as install_theme_base, install_theme_fileobj


LOGGER = logging.getLogger(__name__)


class ThemePackageListAPIView(ThemePackageMixin, GenericAPIView):
    """
    POST uploads a new theme package with templates
    to override the default ones.
    """

    parser_classes = (parsers.FormParser, parsers.MultiPartParser,
        parsers.JSONParser)
    serializer_class = ThemePackageSerializer

    def install_theme(self, package_uri):
        install_theme_base(self.theme, package_uri, force=True)

    def post(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        package_uri = request.data.get('location', None)
        if package_uri and 'aws.com/' in package_uri:
            self.install_theme(package_uri)
        elif 'file' in request.FILES:
            package_file = request.FILES['file']
            LOGGER.info("install %s to %s", package_uri, self.theme)
            try:
                with zipfile.ZipFile(package_file, 'r') as zip_file:
                    install_theme_fileobj(self.theme, zip_file, force=True)
            finally:
                if hasattr(package_file, 'close'):
                    package_file.close()
        else:
            return Response({'details': "no package_uri or file specified."},
                status=status.HTTP_400_BAD_REQUEST)
        return Response({'location': package_uri})
