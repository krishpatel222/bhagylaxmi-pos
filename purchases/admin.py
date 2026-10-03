from django.contrib import admin
from .models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ('gst_amount', 'line_total')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('purchase_id', 'supplier', 'invoice_number', 'purchase_date', 'grand_total', 'paid_amount', 'pending_amount', 'payment_status', 'stock_posted', 'created_by')
    list_filter = ('payment_status', 'stock_posted', 'purchase_date', 'supplier')
    search_fields = ('purchase_id', 'invoice_number', 'supplier__name', 'supplier__company_name')
    readonly_fields = ('purchase_id', 'subtotal', 'gst_amount', 'grand_total', 'pending_amount', 'stock_posted', 'created_by', 'created_at', 'updated_at')
    inlines = [PurchaseItemInline]
    ordering = ('-created_at',)
