# Create your views here.
from pages.views import PageView
from pages.mixins import TemplateChoiceMixin

class HomeView(TemplateChoiceMixin, PageView):
    template_name = "index.html"
