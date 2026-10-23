from django.contrib import admin
from .models import DrugInfo, Alternative


@admin.register(DrugInfo)
class DrugInfoAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'usual_dose')
    search_fields = ('medicine__name',)


@admin.register(Alternative)
class AlternativeAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'alternative', 'note')