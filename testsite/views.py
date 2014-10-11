# Create your views here.
from pages.views import PageView
from django.views.generic import TemplateView
from pages.mixins import TemplateChoiceMixin

class HomeView(TemplateChoiceMixin, PageView):
    template_name = "index.html"

class UploadedTemplatesView(TemplateView):
    template_name = "uploadedtemplate_list.html"
