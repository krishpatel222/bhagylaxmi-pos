from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'name', 'gujarati_name', 'category', 'brand', 'purchase_price', 'selling_price', 'mrp', 'current_stock', 'unit', 'is_active')
    list_filter = ('category', 'brand', 'is_active', 'unit')
    search_fields = ('product_id', 'name', 'gujarati_name', 'sku', 'barcode')
    readonly_fields = ('product_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
