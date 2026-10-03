from django.contrib import admin
from .models import InventoryTransaction


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'transaction_type', 'quantity', 'previous_stock', 'new_stock', 'created_by', 'created_at')
    list_filter = ('transaction_type', 'created_at', 'reference_type')
    search_fields = ('product__name', 'product__product_id', 'product__sku', 'reference_id', 'note')
    readonly_fields = ('product', 'transaction_type', 'quantity', 'previous_stock', 'new_stock', 'reference_type', 'reference_id', 'note', 'created_by', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        # Prevent manual creation via admin interface (Use Stock Adjustment view or change_stock service)
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting transaction audit logs
        return False
