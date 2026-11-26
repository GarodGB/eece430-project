from django.contrib import admin

from .models import DamanStatement, InsuranceClaim


# PHAR-16: claims and statements are created only by the app (sales and the
# Insurance Claims page). In /admin they are READ-ONLY, so money owed by Daman
# can't be changed by hand.

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ClaimInline(admin.TabularInline):
    model = InsuranceClaim
    extra = 0
    fields = ('sale', 'policy_number', 'amount', 'status')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(ReadOnlyAdmin):
    list_display = ('id', 'insurer', 'policy_number', 'amount', 'status', 'statement',
                    'submitted_at')
    list_filter = ('status', 'insurer')


@admin.register(DamanStatement)
class DamanStatementAdmin(ReadOnlyAdmin):
    list_display = ('number', 'pharmacy', 'status', 'total', 'created_at', 'paid_at')
    list_filter = ('status', 'pharmacy')
    inlines = [ClaimInline]
