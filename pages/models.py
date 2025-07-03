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

from __future__ import unicode_literals

import datetime, json, logging, random
from collections import OrderedDict

import markdown
from bs4 import BeautifulSoup
from deployutils.helpers import datetime_or_now
from django.contrib.auth import get_user_model
from django.db import IntegrityError, models, transaction
from django.db.models import Max, Q
from django.template.defaultfilters import slugify
from rest_framework.exceptions import ValidationError

from . import settings
from .compat import (gettext_lazy as _, import_string,
    python_2_unicode_compatible, reverse, six)


LOGGER = logging.getLogger(__name__)


def get_extra_field_class():
    extra_class = settings.EXTRA_FIELD
    if extra_class is None:
        extra_class = models.TextField
    elif isinstance(extra_class, str):
        extra_class = import_string(extra_class)
    return extra_class


class RelationShipManager(models.Manager):

    def insert_available_rank(self, root, pos=0, node=None):
        # Implementation Note:
        #   Edges are ordered loosily. That is: only when a node is specified
        #   to be at a specific position in the outbound adjency list from
        #   an origin node will ranks be computed. By default all ranks
        #   are zero.
        #   This means we can end-up in the following situations before
        #   inserting a node:
        #      (sort order 0 1 2 3 4 5 6)
        #   1. rank        0 0 0 0 0 0 0
        #   2. rank        6 6 6 6 6 6 6
        #   insertion pos      ^
        #   The resulting ranks must keep the current order yet leave
        #   a hole to insert the new node.
        #   1. new rank    0 0 3 4 5 6 7
        #   2. new rank    0 1 6 6 6 6 6
        sorted_edges = list(self.filter(orig_element=root).order_by(
            'rank', 'pk'))

        if node:
            for index, edge in enumerate(sorted_edges):
                if edge.dest_element_id == node.pk:
                    prev_pos = index
                    break
            if prev_pos < pos:
                pos = pos + 1

        for index, edge in enumerate(sorted_edges[:pos]):
            if edge.rank >= pos:
                edge.rank = index
                edge.save()
        for index, edge in enumerate(sorted_edges[pos:]):
            if edge.rank < (pos + index + 1):
                edge.rank = pos + index + 1
                edge.save()

    def insert_node(self, root, node, pos=0):
        """
        Insert a *node* at a specific position in the list of outbound
        edges from *root*.
        """
        with transaction.atomic():
            self.insert_available_rank(root, pos=pos)
            self.create(orig_element=root, dest_element=node, rank=pos)


@python_2_unicode_compatible
class RelationShip(models.Model):
    """
    Encodes a relation between two ``PageElement``.
    """
    objects = RelationShipManager()

    orig_element = models.ForeignKey(
        "PageElement", on_delete=models.CASCADE, related_name='from_element')
    dest_element = models.ForeignKey(
        "PageElement", on_delete=models.CASCADE, related_name='to_element')
    tag = models.SlugField(null=True)
    rank = models.IntegerField(default=0)

    class Meta:
        unique_together = ('orig_element', 'dest_element')

    def __str__(self):
        return "%s to %s" % (
            self.orig_element.slug, self.dest_element.slug) #pylint: disable=no-member


class PageElementQuerySet(models.QuerySet):

    def build_content_tree(self, prefix="", cut=None,
                           visibility=None, accounts=None):
        return build_content_tree(roots=self, prefix=prefix,
            cut=cut, visibility=visibility, accounts=accounts)


class PageElementManager(models.Manager):

    def get_queryset(self):
        return PageElementQuerySet(self.model, using=self._db)

    def filter_available(self, visibility=None, accounts=None,
                         start_at=None, ends_at=None):
        filtered_in = None
        if visibility:
            for visible in visibility:
                visibility_q = Q(extra__contains=visible)
                if filtered_in:
                    filtered_in |= visibility_q
                else:
                    filtered_in = visibility_q
        if accounts:
            accounts_q = Q(account__slug__in=accounts)
            if filtered_in:
                filtered_in |= accounts_q
            else:
                filtered_in = accounts_q
        queryset = self.filter(filtered_in) if filtered_in else self.all()

        filtered_dates = {}
        if start_at:
            filtered_dates.update({'text_updated_at__gte': start_at})
        if ends_at:
            filtered_dates.update({'text_updated_at__lt': ends_at})
        return queryset.filter(**filtered_dates)


    def get_roots(self, visibility=None, accounts=None):
        queryset = self.filter_available(
            visibility=visibility, accounts=accounts).extra(where=[
            '(SELECT COUNT(*) FROM pages_relationship'\
            ' WHERE pages_relationship.dest_element_id = pages_pageelement.id)'\
            ' = 0'])
        return queryset

    def get_leafs(self):
        return self.all().extra(where=[
            '(SELECT COUNT(*) FROM pages_relationship'\
            ' WHERE pages_relationship.orig_element_id = pages_pageelement.id)'\
            ' = 0'])

    @staticmethod
    def followed_by(user):
        return PageElement.objects.filter(followers__user=user)


@python_2_unicode_compatible
class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """
    #pylint:disable=too-many-instance-attributes
    objects = PageElementManager()

    FORMAT_CHOICES = (
        ('HTML', 'HTML'),
        ('MD', 'Markdown'),
    )

    slug = models.SlugField(unique=True,
        help_text=_("Unique identifier that can be used in URL paths"))
    title = models.CharField(max_length=1024, blank=True,
        help_text=_("Title of the page element"))
    content_format = models.CharField(
        max_length=4, choices=FORMAT_CHOICES, default='HTML',
        help_text=_("Designate whether the text field is HTML or Markdown"))
    text = models.TextField(blank=True,
        help_text=_("Long description of the page element"))
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='account_page_element',
        null=True, on_delete=models.SET_NULL)
    picture = models.URLField(_("URL to a icon picture"), max_length=2083,
        null=True, blank=True, help_text=_("Icon picture"))
    reading_time = models.DurationField(null=True,
        default=datetime.timedelta,  # stored in microseconds
        help_text=_("Reading time of the material (in hh:mm:ss)"))
    lang = models.CharField(default=settings.LANGUAGE_CODE, max_length=8,
        help_text=_("Language the material is written in"))
    text_updated_at = models.DateTimeField(auto_now_add=True,
        help_text=_("Last updated at date for the text field"))
    extra = get_extra_field_class()(null=True, blank=True)
    relationships = models.ManyToManyField("self",
        related_name='related_to', through='RelationShip', symmetrical=False)

    def __str__(self):
        return self.slug

    @property
    def descr(self):
        #pylint:disable=attribute-defined-outside-init
        if not hasattr(self, '_descr'):
            self._descr = self.get_descr()
        return self._descr

    @property
    def html_formatted(self):
        #pylint:disable=attribute-defined-outside-init
        if not hasattr(self, '_html_formatted'):
            self._html_formatted = self.get_html_formatted()
        return self._html_formatted

    @property
    def nb_upvotes(self):
        return Vote.objects.filter(element=self, vote=Vote.UP_VOTE).count()

    @property
    def nb_followers(self):
        return Follow.objects.filter(element=self).count()

    def add_relationship(self, element, tag=None):
        rank = RelationShip.objects.filter(
            orig_element=self).aggregate(Max('rank')).get('rank__max', None)
        if rank is None:
            rank = 0
        return RelationShip.objects.get_or_create(
            orig_element=self, dest_element=element,
            defaults={'tag': tag, 'rank': rank})

    def remove_relationship(self, element):
        RelationShip.objects.filter(
            orig_element=self,
            dest_element=element).delete()
        return True

    def get_descr(self):
        #pylint:disable=too-many-nested-blocks
        soup = BeautifulSoup(self.html_formatted, 'html5lib')
        descr = soup.find('p')
        if descr:
            nb_available_characters = 5 * 60 # 5 lines of 60 characters
            short_descr = soup.new_tag(name='p')
            for child in descr.children:
                if child.name:
                    nb_available_characters -= len(child.text)
                    short_descr.append(child)
                else:
                    child_text = child.text
                    child_text_len = len(child_text)
                    if nb_available_characters < child_text_len:
                        for idx in range(nb_available_characters - 1, 0, -1):
                            if child.text[idx] == " ":
                                break
                            nb_available_characters -= 1
                        child_text = child.text[:nb_available_characters]
                        nb_available_characters -= nb_available_characters
                    else:
                        nb_available_characters -= child_text_len
                    short_descr.append(child_text)
                if nb_available_characters < 0:
                    break

            # `string=` requires BeautifulSoup4>=4.13
            tag = soup.new_tag(name='a',
                href=reverse('pages_element', args=(self.slug,)))
            tag.append("... read more")
            short_descr.append(tag)
            return str(short_descr)
        return ""

    def get_html_formatted(self):
        content_format = self.content_format
        text = self.text
        if content_format and content_format == 'HTML':
            return text
        return markdown.markdown(text, extensions=['tables'])


    def get_parent_paths(self, depth=None, hints=None):
        """
        Returns a list of paths.

        When *depth* is specified each paths will be *depth* long or shorter.
        When *hints* is specified, it is a list of elements in a path. The
        paths returns will contain *hints* along the way.
        """
        #pylint:disable=too-many-nested-blocks
        if depth is not None and depth == 0:
            return [[self]]
        results = []
        parents = PageElement.objects.filter(
            pk__in=RelationShip.objects.filter(
                dest_element=self).values('orig_element_id'))
        if not parents:
            return [[self]]
        if hints:
            for parent in parents:
                if parent.slug == str(hints[-1]):
                    # we found a way to cut the search space early.
                    parents = [parent]
                    hints = hints[:-1]
                    break
        for parent in parents:
            grandparents = parent.get_parent_paths(
                depth=(depth - 1) if depth is not None else None,
                hints=hints)
            if grandparents:
                for grandparent in grandparents:
                    term_index = 0
                    if hints:
                        for node in grandparent:
                            if node.slug == str(hints[term_index]):
                                term_index += 1
                                if term_index >= len(hints):
                                    break
                    if not hints or term_index >= len(hints):
                        # we have not hints or we consumed all of them.
                        results += [grandparent + [self]]
        return results

    def get_relationships(self, tag=None):
        if not tag:
            return self.relationships.filter(
                to_element__orig_element=self)
        return self.relationships.filter(
            to_element__tag=tag, to_element__orig_element=self)

    def get_related_to(self, tag):
        return self.related_to.filter(
            from_element__tag=tag,
            from_element__dest_element=self)

    def __init__(self, *args, **kwargs):
        super(PageElement, self).__init__(*args, **kwargs)
        self.__original_text = self.text

    def save(self, *args, force_insert=False, force_update=False,
             using=None, update_fields=None):
        if self.__original_text != self.text:
            self.text_updated_at = datetime_or_now()

        if self.slug: # serializer will set created slug to '' instead of None.
            return super(PageElement, self).save(
                force_insert=force_insert, force_update=force_update,
                using=using, update_fields=update_fields)
        max_length = self._meta.get_field('slug').max_length
        slug_base = slugify(self.title)
        if not slug_base:
            # title might be empty
            "".join([random.choice("abcdef0123456789") for _ in range(7)])
        elif len(slug_base) > max_length:
            slug_base = slug_base[:max_length]
        self.slug = slug_base
        for _ in range(1, 10):
            try:
                with transaction.atomic():
                    return super(PageElement, self).save(
                        force_insert=force_insert, force_update=force_update,
                        using=using, update_fields=update_fields)
            except IntegrityError as err:
                if 'uniq' not in str(err).lower():
                    raise
                suffix = '-%s' % "".join([random.choice("abcdef0123456789")
                    for _ in range(7)])
                if len(slug_base) + len(suffix) > max_length:
                    self.slug = slug_base[:(max_length - len(suffix))] + suffix
                else:
                    self.slug = slug_base + suffix
        raise ValidationError({'detail':
            "Unable to create a unique URL slug from title '%s'" % self.title})


@python_2_unicode_compatible
class Comment(models.Model):
    """
    A user comments about a PageElement.
    """
    created_at = models.DateTimeField(default=None, db_index=True,
        help_text=_("Date/time the comment was submitted (in ISO format)"))
    text = models.TextField(max_length=settings.COMMENT_MAX_LENGTH,
        help_text=_("Text of the comment"))
    ip_address = models.GenericIPAddressField(_('IP address'),
        unpack_ipv4=True, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
        related_name="%(class)s_comments", on_delete=models.CASCADE,
        help_text=_("User that submitted the comment"))
    element = models.ForeignKey(PageElement, on_delete=models.CASCADE,
        related_name='comments')

    def __str__(self):
        return str(self.text)


class FollowManager(models.Manager):

    @staticmethod
    def get_followers(element):
        """
        Get a list of followers for a Element.
        """
        return get_user_model().objects.filter(follows__element=element)

    def subscribe(self, element, user):
        """
        Subscribe a User to changes to a Element.
        """
        self.get_or_create(user=user, element=element)

    def unsubscribe(self, element, user):
        """
        Unsubscribe a User from changes to a Element.
        """
        try:
            self.get(user=user, element=element).delete()
        except models.ObjectDoesNotExist:
            pass


@python_2_unicode_compatible
class Follow(models.Model):
    """
    A relationship intended for a User to follow comments on a Element.
    """
    objects = FollowManager()

    created_at = models.DateTimeField(editable=False, auto_now_add=True,
        help_text=_("Date/time the follow was created (in ISO format)"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_column='user_id',
         related_name='follows', on_delete=models.CASCADE)
    element = models.ForeignKey(PageElement,
        related_name='followers', on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(default=datetime_or_now,
        help_text=_("Last date/time the element was read by the user"))

    class Meta:
        unique_together = (('user', 'element'),)

    def __str__(self):
        return '%s follows %s' % (self.user, self.element)


@python_2_unicode_compatible
class LiveEvent(models.Model):
    """
    A live webinar, onsite classroom, etc.
    """
    element = models.ForeignKey(PageElement, on_delete=models.CASCADE,
        related_name='events')
    created_at = models.DateTimeField(editable=False, auto_now_add=True,
        help_text=_("Date/time the live event was created (in ISO format)"))
    scheduled_at = models.DateTimeField(null=True,
        help_text=_("Date/time the live event is scheduled (in ISO format)"))
    location = models.URLField(_("URL to the calendar event"), max_length=2083)
    max_attendees = models.IntegerField(default=0)
    extra = get_extra_field_class()(null=True, blank=True,
        help_text=_("Extra meta data (can be stringify JSON)"))

    def __str__(self):
        return "%s-live" % str(self.element)


@python_2_unicode_compatible
class Sequence(models.Model):
    """
    Sequence of `PageElement` typically used to implement courses
    """
    created_at = models.DateTimeField(editable=False, auto_now_add=True,
        help_text=_("Date/time the sequence was created (in ISO format)"))
    slug = models.SlugField(unique=True,
        help_text=_("Unique identifier that can be used in URL paths"))
    title = models.CharField(max_length=1024, blank=True,
        help_text=_("Title of the sequence"))
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='account_sequences',
        null=True, on_delete=models.SET_NULL,
        help_text=_("Account that can edit the sequence"))
    has_certificate = models.BooleanField(default=False,
        help_text=_("True when the sequence ends with a certificate"\
        " of completion"))
    extra = get_extra_field_class()(null=True, blank=True,
        help_text=_("Extra meta data (can be stringify JSON)"))

    def __str__(self):
        return "%s" % str(self.slug)

    @property
    def get_certificate(self):
        if self.has_certificate:
            return self.get_last_element.content
        return None

    @property
    def get_last_element(self):
        return self.sequence_enumerated_elements.order_by(
            'rank').last()


@python_2_unicode_compatible
class EnumeratedElements(models.Model):
    """
    One element in a sequence
    """
    sequence = models.ForeignKey(Sequence, on_delete=models.CASCADE,
                                 related_name='sequence_enumerated_elements')
    content = models.ForeignKey(PageElement, on_delete=models.CASCADE)
    rank = models.IntegerField(
        help_text=_("Used to order elements when presenting a sequence"))
    min_viewing_duration = models.DurationField(
        default=datetime.timedelta,  # stored in microseconds
        help_text=_("Minimum viewing time of the material (in hh:mm:ss)"))

    class Meta:
        unique_together = ('sequence', 'rank')

    def __str__(self):
        return "%s-%d" % (self.sequence, self.rank)


@python_2_unicode_compatible
class SequenceProgress(models.Model):
    """
    Progress of a `User` going through a sequence.
    """
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    sequence = models.ForeignKey(Sequence, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completion_date = models.DateTimeField(blank=True, null=True,
        help_text=_("Time when the user completed the Sequence"))
    extra = get_extra_field_class()(null=True, blank=True,
        help_text=_("Extra meta data (can be stringify JSON)"))

    def __str__(self):
        return "%s-%s" % (self.sequence, self.user)

    @property
    def is_completed(self):
        if self.sequence.has_certificate:
            # We exclude the element with the highest rank
            certificate_element = self.sequence.get_certificate
            enumerated_elements = EnumeratedElements.objects.filter(
                sequence=self.sequence).exclude(
                content__slug=certificate_element.slug)
        else:
            enumerated_elements = EnumeratedElements.objects.filter(
                sequence=self.sequence).order_by('rank')
        user_enumerated_progress = EnumeratedProgress.objects.filter(
            progress=self,
            rank__in=enumerated_elements.values_list(
            'rank', flat=True))
        for element in enumerated_elements:
            if not user_enumerated_progress.filter(
                    rank=element.rank,
                    viewing_duration__gte=element.min_viewing_duration
            ).exists():
                return False
        return True


@python_2_unicode_compatible
class EnumeratedProgress(models.Model):
    """
    Progress of a `User` on each element of a sequence.
    """
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    sequence_progress = models.ForeignKey(
        SequenceProgress, on_delete=models.CASCADE)
    step = models.ForeignKey(EnumeratedElements, on_delete=models.CASCADE)
    viewing_duration = models.DurationField(
        default=datetime.timedelta,  # stored in microseconds
        help_text=_("Total recorded viewing time for the material"))
    last_ping_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp of the last activity ping"))

    class Meta:
        unique_together = ('sequence_progress', 'step')

    def __str__(self):
        return "%s-%s" % (self.sequence_progress.user, self.step)

    # Implementation Note on the following properties:
    # We are using a derivative of `EnumeratedElementsSerializer`
    # to return an `EnumeratedProgress` instance.

    @property
    def content(self):
        return self.step.content

    @property
    def min_viewing_duration(self):
        return self.step.min_viewing_duration

    @property
    def rank(self):
        return self.step.rank

    @property
    def sequence(self):
        return self.step.sequence


class VoteManager(models.Manager):

    def vote_up(self, element, user):
        """
        Vote a Element up by a User.
        """
        vote, created = self.get_or_create(user=user, element=element,
            defaults={'vote': Vote.UP_VOTE})
        if not created:
            vote.vote = Vote.UP_VOTE
            vote.save()

    def vote_down(self, element, user):
        """
        Vote a Element down by a User.
        """
        vote, created = self.get_or_create(user=user, element=element,
            defaults={'vote': Vote.DOWN_VOTE})
        if not created:
            vote.vote = Vote.DOWN_VOTE
            vote.save()


@python_2_unicode_compatible
class Vote(models.Model):
    """
    A vote on an element by a User.
    """
    objects = VoteManager()

    UP_VOTE = 1
    DOWN_VOTE = -1
    SCORES = (
        (UP_VOTE, '+1'),
        (DOWN_VOTE, '-1'),
    )

    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    element = models.ForeignKey(PageElement,
        related_name='votes', on_delete=models.CASCADE)
    vote = models.SmallIntegerField(choices=SCORES)

    class Meta:
        # One vote per user per Element
        unique_together = (('user', 'element'),)

    def __str__(self):
        return "%s: %s on %s" % (self.user, self.vote, self.element)

    def is_upvote(self):
        return self.vote == self.UP_VOTE

    def is_downvote(self):
        return self.vote == self.DOWN_VOTE


def build_content_tree(roots=None, prefix=None, cut=None,
                       visibility=None, accounts=None):
    """
    Returns a content tree from a list of roots.

    code::

        build_content_tree(roots=[PageElement<boxes-and-enclosures>])
        {
          "/boxes-and-enclosures": [
            { ... data for node ... },
            {
              "boxes-and-enclosures/management": [
              { ... data for node ... },
              {}],
              "boxes-and-enclosures/design": [
              { ... data for node ... },
              {}],
            }]
        }
    """
    #pylint:disable=too-many-locals,too-many-statements
    # Implementation Note: The structure of the content in the database
    # is stored in terms of `PageElement` (node) and `Relationship` (edge).
    # We use a breadth-first search algorithm here such as to minimize
    # the number of queries to the database.
    LOGGER.debug("build_content_tree"\
        "(roots=%s, prefix=%s, cut=%s, visibility=%s, accounts=%s)",
        roots, prefix, cut, visibility, accounts)
    if roots is None:
        roots = PageElement.objects.get_roots(
            visibility=visibility, accounts=accounts).order_by(
            '-account_id', 'title')
        if prefix and prefix != '/':
            LOGGER.warning("[build_content_tree] prefix=%s but no roots"\
                " were defined", prefix)
        else:
            prefix = ''
    else:
        if not prefix:
            LOGGER.warning("[build_content_tree] roots=%s but not prefix"\
                " was defined", roots)
    # insures the `prefix` will match a `PATH_RE` (starts with a '/' and
    # does not end with one).
    if not prefix.startswith("/"):
        prefix = '/%s' % prefix
    prefix = prefix.rstrip('/')
    filtered_in = None
    if visibility:
        for visible in visibility:
            visibility_q = Q(dest_element__extra__contains=visible)
            if filtered_in:
                filtered_in |= visibility_q
            else:
                filtered_in = visibility_q
    if accounts:
        accounts_q = Q(dest_element__account__slug__in=accounts)
        if filtered_in:
            filtered_in |= accounts_q
        else:
            filtered_in = accounts_q
    edges_qs = (RelationShip.objects.filter(filtered_in)
        if filtered_in else  RelationShip.objects.all())

    results = OrderedDict()
    pks_to_leafs = {}
    roots_after_cut = []
    for root in roots:
        if isinstance(root, PageElement):
            slug = root.slug
            orig_element_id = root.pk
            title = root.title
            picture = root.picture
            extra = root.extra
            text = root.text
        else:
            slug = root.get('slug', root.get('dest_element__slug'))
            orig_element_id = root.get('dest_element__pk')
            title = root.get('dest_element__title')
            picture = root.get('dest_element__picture')
            extra = root.get('dest_element__extra')
            text = root.get('dest_element__text', None)
        leaf_slug = '/%s' % slug
        if prefix.endswith(leaf_slug):
            # Workaround because we sometimes pass a prefix and sometimes
            # a path `from_root`.
            base = prefix
        else:
            base = prefix + leaf_slug
        try:
            extra = json.loads(extra)
        except (TypeError, ValueError):
            pass
        result_node = {'slug': slug, 'title': title}
        if picture:
            result_node.update({'picture': picture})
        if extra:
            result_node.update({'extra': extra})
        if text:
            result_node.update({'text': text})
        pks_to_leafs[orig_element_id] = {
            'path': base,
            'node': (result_node, OrderedDict())
        }
        results.update({base: pks_to_leafs[orig_element_id]['node']})
        if cut is None or cut.enter(extra):
            roots_after_cut += [root]

    args = tuple([])
    edges = edges_qs.filter(
        orig_element__in=roots_after_cut).values(
        'orig_element_id', 'dest_element_id', 'rank', 'dest_element__slug',
        'dest_element__extra', 'dest_element__picture', 'dest_element__title',
        *args).order_by('rank', 'pk')
    while edges:
        next_pks_to_leafs = {}
        for edge in edges:
            orig_element_id = edge.get('orig_element_id')
            dest_element_id = edge.get('dest_element_id')
            slug = edge.get('slug', edge.get('dest_element__slug'))
            base = pks_to_leafs[orig_element_id]['path'] + "/" + slug
            title = edge.get('dest_element__title')
            picture = edge.get('dest_element__picture')
            extra = edge.get('dest_element__extra')
            try:
                extra = json.loads(extra)
            except (TypeError, ValueError):
                pass
            result_node = {'slug': slug, 'title': title}
            if picture:
                result_node.update({'picture': picture})
            if extra:
                result_node.update({'extra': extra})
            text = edge.get('dest_element__text', None)
            if text:
                result_node.update({'text': text})
            pivot = (result_node, OrderedDict())
            pks_to_leafs[orig_element_id]['node'][1].update({base: pivot})
            if cut is None or cut.enter(extra):
                next_pks_to_leafs[dest_element_id] = {
                    'path': base,
                    'node': pivot
                }
        pks_to_leafs = next_pks_to_leafs
        next_pks_to_leafs = {}
        edges = edges_qs.filter(
            orig_element_id__in=pks_to_leafs.keys()).values(
            'orig_element_id', 'dest_element_id', 'rank', 'dest_element__slug',
            'dest_element__extra', 'dest_element__picture',
            'dest_element__title', *args).order_by('rank', 'pk')
    return results


def flatten_content_tree(roots, sort_by_key=True, depth=0):
    """
    Transforms a tree into a list with ``indent`` as the depth of a node
    in the original tree.
    """
    results = []
    children = six.iteritems(roots)
    if sort_by_key:
        children = sorted(children,
            key=lambda node: (
                node[1][0].get('rank', 0)
                if node[1][0].get('rank') is not None else 0,
                node[1][0].get('title', "")))
    for key, values in children:
        elem, nodes = values
        elem.update({
            'path': key,
            'indent': depth
        })
        results += [elem]
        results += flatten_content_tree(nodes,
            sort_by_key=sort_by_key, depth=depth + 1)
    return results
