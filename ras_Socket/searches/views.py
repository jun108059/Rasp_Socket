from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.db.models import Q

from .models import Search


class HomePageView(TemplateView):
    template_name = 'home.html'


class SearchResultsView(ListView):
    model = Search
    template_name = 'search_results.html'

    def get_queryset(self):  # new
        query = self.request.GET.get('q')
        object_list = Search.objects.filter(
            Q(name__icontains=query) | Q(state__icontains=query)
        )
        return object_list