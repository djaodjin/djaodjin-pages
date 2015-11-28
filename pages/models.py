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

import logging

from django.db import models

from . import settings

LOGGER = logging.getLogger(__name__)

class RelationShip(models.Model):
    orig_element = models.ForeignKey(
        "PageElement", related_name='from_element')
    dest_element = models.ForeignKey(
        "PageElement", related_name='to_element', blank=True, null=True)
    tag = models.SlugField()

    def __unicode__(self):
        return "%s to %s" % (
            self.orig_element.slug, self.dest_element.slug) #pylint: disable=no-member

class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=150, blank=True)
    text = models.TextField(blank=True)
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='account_page_element', null=True)
    relationships = models.ManyToManyField("self",
        related_name='related_to', through='RelationShip', symmetrical=False)
    tag = models.SlugField(null=True, blank=True)

    def add_relationship(self, element, tag):
        relationship, created = RelationShip.objects.get_or_create(
            orig_element=self,
            dest_element=element,
            tag=tag)
        return relationship, created

    def remove_relationship(self, element):
        RelationShip.objects.filter(
            orig_element=self,
            dest_element=element).delete()
        return True

    def get_relationships(self, tag=None):
        if not tag:
            return self.relationships.filter(
                to_element__orig_element=self)
        else:
            return self.relationships.filter(
                to_element__tag=tag,
                to_element__orig_element=self)

    def get_related_to(self, tag):
        return self.related_to.filter(
            from_element__tag=tag,
            from_element__dest_element=self)

    def __unicode__(self):
        return self.slug


class MediaTag(models.Model):

    location = models.CharField(max_length=250)
    tag = models.CharField(max_length=50)

    def __unicode__(self):
        return unicode(self.tag)


class ThemePackage(models.Model):
    """
    This model allow to record uploaded template.
    """
    slug = models.SlugField(unique=True)
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL,
        related_name='account_template', null=True, blank=True)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        if self.account:
            return '%s-%s' % (self.account, self.name)
        else:
            return self.name

def get_active_theme():
    """
    Returns the active theme from a request.
    """
    if settings.ACTIVE_THEME_CALLABLE:
        from pages.compat import import_string
        theme_slug, account = import_string(settings.ACTIVE_THEME_CALLABLE)()
        LOGGER.debug("pages: get_active_theme('%s')", theme_slug)
        try:
            return ThemePackage.objects.get(
                slug=theme_slug,
                account=account)
        except ThemePackage.DoesNotExist:
            return None
    return ThemePackage.objects.all().first()
