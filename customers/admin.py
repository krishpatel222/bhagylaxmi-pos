from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'name', 'mobile', 'city', 'gst_number', 'opening_balance', 'is_active', 'created_at')
    list_filter = ('is_active', 'city', 'state', 'created_at')
    search_fields = ('customer_id', 'name', 'mobile', 'whatsapp', 'email', 'gst_number')
    readonly_fields = ('customer_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
