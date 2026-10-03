from django.contrib import admin
from .models import SalesReturn, SalesReturnItem


class SalesReturnItemInline(admin.TabularInline):
    model = SalesReturnItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'refund_amount')


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ('return_id', 'sale', 'customer', 'return_date', 'refund_amount', 'created_by')
    search_fields = ('return_id', 'sale__sale_id', 'customer__name', 'reason')
    readonly_fields = ('return_id', 'created_at')
    inlines = [SalesReturnItemInline]
