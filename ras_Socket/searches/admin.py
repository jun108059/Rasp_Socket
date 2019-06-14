from django.contrib import admin
from .models import Search


class SearchAdmin(admin.ModelAdmin):
    list_display = ("name", "state",)


admin.site.register(Search, SearchAdmin)
