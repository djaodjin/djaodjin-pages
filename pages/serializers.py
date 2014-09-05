from rest_framework import serializers
from .models import PageElement

#pylint: disable=no-init
#pylint: disable=old-style-class

class PageElementSerializer(serializers.ModelSerializer):

    class Meta:
        model = PageElement
        fields = ('slug', 'text')
        read_only_fields = ('slug',)
