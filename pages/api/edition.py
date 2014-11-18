#pylint: disable=no-init,no-member,unused-variable
#pylint: disable=old-style-class,line-too-long,maybe-no-member

import os, random, string, re

from bs4 import BeautifulSoup

from django.conf import settings

from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from pages.models import PageElement, UploadedImage
from pages.serializers import PageElementSerializer

from pages.encrypt_path import decode

from pages.mixins import AccountMixin


class PageElementDetail(AccountMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an editable element on a ``Page``.
    """
    model = PageElement
    serializer_class = PageElementSerializer

    @staticmethod
    def clean_text(text):
        formatted_text = re.sub(r'[\ ]{2,}', '', text)
        if formatted_text.startswith('\n'):
            formatted_text = formatted_text[1:]
        if formatted_text.endswith('\n'):
            formatted_text = formatted_text[:len(formatted_text)-1]
        return formatted_text

    def write_html(self, path, new_id):
        with open(path, "r") as myfile:
            soup = BeautifulSoup(myfile, "html5lib")
            soup_elements = soup.find_all(self.request.DATA['tag'].lower())
            if len(soup_elements) > 1:
                for element in soup_elements:
                    if element.string:
                        formatted_text = self.clean_text(element.string)
                        if formatted_text == self.request.DATA['old_text']:
                            soup_element = element
                            break
                if not soup_element:
                    # XXX - raise an exception
                    pass
            else:
                soup_element = soup_elements[0]

            soup_element['id'] = new_id
            html = soup.prettify("utf-8")
            changed = True
        if changed:
            # write html to save new id
            with open(path, "w") as myfile:
                myfile.write(html)

    def update_or_create_pagelement(self, request, *args, **kwargs):#pylint: disable=too-many-locals,unused-argument
        """
        Update an existing PageElement if id provided
        If no id provided create a pagelement with new id,
        write new html and return id to live template
        """
        partial = kwargs.pop('partial', False)
        self.object = self.get_object_or_none()
        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.pre_save(serializer.object)
        except ValidationError as err:
            # full_clean on model instance may be called in pre_save,
            # so we have to handle eventual errors.
            return Response(err.message_dict, status=status.HTTP_400_BAD_REQUEST)


        if self.object is None:
            if kwargs.get('slug') != 'undefined':
                new_id = kwargs.get('slug')
            else:
            # Create a new id
                new_id = ''.join(random.choice(string.lowercase) for i in range(10))
                while PageElement.objects.filter(slug__exact=new_id).count() > 0:
                    new_id = ''.join(random.choice(string.lowercase) for i in range(10))

            if not new_id.startswith('djmedia-'):
            # Create a pageelement
                pagelement = PageElement(slug=new_id, text=request.DATA['text'])
                account = self.get_account()
                if account:
                    pagelement.account = account
                serializer = self.get_serializer(pagelement, data=request.DATA,
                    files=request.FILES, partial=partial)
                self.object = serializer.save(force_insert=True)

                changed = False
                template_name = request.DATA['template_name']
                template_path = decode(request.DATA['template_path'])
                if template_name:
                    for directory in settings.TEMPLATE_DIRS:
                        for (dirpath, dirnames, filenames) in os.walk(directory):
                            for filename in filenames:
                                if filename == template_name:
                                    path = os.path.join(dirpath, filename)
                elif template_path:
                    path = template_path
                self.write_html(path, new_id)
                self.post_save(self.object, created=True)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                account = self.get_account()
                text = request.DATA['text']
                #check S3 version exists
                if not 's3.amazon' in text:
                    try:
                        upload_image = UploadedImage.objects.get(
                            uploaded_file_temp=text.replace('/media/', ''))
                        if upload_image.uploaded_file:
                            text = settings.S3_URL + '/' + text.replace('/media/', '')
                    except: #pylint: disable=bare-except
                        pass
                pagelement = PageElement(slug=new_id, text=text)
                if account:
                    pagelement.account = account
                serializer = self.get_serializer(pagelement, data=request.DATA,
                    files=request.FILES, partial=partial)
                self.object = serializer.save(force_insert=True)
        self.object = serializer.save(force_update=True)
        self.post_save(self.object, created=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.update_or_create_pagelement(request, *args, **kwargs)
