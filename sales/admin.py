from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'selling_price', 'mrp', 'gst_rate', 'gst_amount', 'discount', 'line_total')
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_id', 'customer', 'sale_date', 'grand_total', 'paid_amount', 'pending_amount', 'payment_method', 'payment_status', 'created_by')
    list_filter = ('payment_status', 'payment_method', 'created_by', 'sale_date')
    search_fields = ('sale_id', 'customer__name', 'customer__mobile')
    readonly_fields = ('sale_id', 'created_at', 'updated_at')
    list_select_related = ('customer', 'created_by')
    inlines = [SaleItemInline]
    ordering = ('-created_at',)

    def has_delete_permission(self, request, obj=None):
        # Prevent physical deletion of financial sale records
        return False
