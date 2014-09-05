# Create your views here.
from django.views.generic import TemplateView
from pages.views import PageView

# class HomeView(TemplateView):
#     template_name = "index.html"

class HomeView(PageView):
	template_name = "index.html"