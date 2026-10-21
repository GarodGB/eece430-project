from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Pharmacy, User

admin.site.register(Pharmacy)


class PharmaLinkUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('PharmaLink', {'fields': ('role', 'pharmacy')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('PharmaLink', {'fields': ('role', 'pharmacy')}),
    )
    list_display = ('username', 'role', 'pharmacy')


admin.site.register(User, PharmaLinkUserAdmin)