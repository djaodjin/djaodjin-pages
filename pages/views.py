from bs4 import BeautifulSoup
from django.views.generic import TemplateView
from pages.models import PageElement
from django.template.response import TemplateResponse
import markdown, re

from django.core.exceptions import ImproperlyConfigured

class PageView(TemplateView):
    """
    Display or Edit a ``Page`` of a ``Project``.

    """

    http_method_names = ['get']

    def get_context_data(self, **kwargs):
        context = super(PageView, self).get_context_data(**kwargs)
        context.update({'template_name': self.template_name})
        return context

    def get(self, request, *args, **kwargs):
        response = super(PageView, self).get(request, *args, **kwargs)

        if self.template_name and isinstance(response, TemplateResponse):
            response.render()
            soup = BeautifulSoup(response.content)
            for editable in soup.find_all(class_="editable"):
                try:
                    id_element = editable['id']
                except:
                    continue
                    # raise ImproperlyConfigured("Unable to find id for \n\n %s.\
                    #     \n\nDon't forget to initialize templates.\
                    #     \n $ python manage.py init_template" % editable)
                try:
                    edit = PageElement.objects.get(slug=id_element)
                    new_text = re.sub(r'[\ ]{2,}', '', edit.text)
                    if 'edit-markdown' in editable['class']:
                        new_text = markdown.markdown(new_text)
                        new_text = BeautifulSoup(new_text)
                        editable.name = 'div'
                        editable.string = ''
                        children_done = []
                        for element in new_text.find_all():
                            if element.name != 'html' and element.name != 'body':
                                if len(element.findChildren()) > 0:
                                    element.append(element.findChildren()[0])
                                    children_done += [element.findChildren()[0]]
                                if not element in children_done:
                                    editable.append(element)
                    else:
                        editable.string = new_text
                except PageElement.DoesNotExist:
                    pass
            response.content = soup.prettify()
        return response
