from django.contrib import admin
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('supplier_id', 'name', 'company_name', 'mobile', 'city', 'gst_number', 'opening_balance', 'is_active', 'created_at')
    list_filter = ('is_active', 'city', 'state', 'created_at')
    search_fields = ('supplier_id', 'name', 'company_name', 'mobile', 'gst_number')
    readonly_fields = ('supplier_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
