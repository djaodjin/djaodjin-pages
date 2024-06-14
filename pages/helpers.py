# Copyright (c) 2022, Djaodjin Inc.
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

import json

from .compat import six


class ContentCut(object):
    """
    Visitor that cuts down a content tree whenever TAG_PAGEBREAK is encountered.
    """
    TAG_PAGEBREAK = 'pagebreak'

    def __init__(self, tag=TAG_PAGEBREAK, depth=1):
        #pylint:disable=unused-argument
        self.match = tag

    def enter(self, tag):
        if tag and self.match:
            if isinstance(tag, dict):
                if tag.get(self.match, False):
                    return False
                return self.match not in tag.get('tags', [])
            return self.match not in tag
        return True

    def leave(self, attrs, subtrees):
        #pylint:disable=unused-argument
        return True


def get_extra(obj, attr_name, default=None):
    try:
        if isinstance(obj.extra, six.string_types):
            try:
                obj.extra = json.loads(obj.extra)
            except (TypeError, ValueError):
                return default
        extra = obj.extra
    except AttributeError:
        extra = obj.get('extra')
    return extra.get(attr_name, default) if extra else default


def set_extra(obj, attr_name, attr_value):
    prev_val = get_extra(obj, attr_name)

    if not obj.extra:
        # In case we have a None type or empty string, initialize
        # extra as a dict because if we're using this method the intention
        # is to set it to some value.
        obj.extra = {}
    obj.extra.update({attr_name: attr_value})
    return prev_val


def update_context_urls(context, urls):
    if 'urls' in context:
        for key, val in six.iteritems(urls):
            if key in context['urls']:
                if isinstance(val, dict):
                    context['urls'][key].update(val)
                else:
                    # Because organization_create url is added in this mixin
                    # and in ``OrganizationRedirectView``.
                    context['urls'][key] = val
            else:
                context['urls'].update({key: val})
    else:
        context.update({'urls': urls})
    return context
