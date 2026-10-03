from django.contrib import admin
from .models import OnlineOrder, OnlineOrderItem


class OnlineOrderItemInline(admin.TabularInline):
    model = OnlineOrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'selling_price', 'line_total')


@admin.register(OnlineOrder)
class OnlineOrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'customer_name', 'mobile', 'city', 'pincode', 'order_amount', 'payment_status', 'status', 'courier_name', 'tracking_number', 'order_date')
    list_filter = ('status', 'payment_status', 'courier_name', 'order_date')
    search_fields = ('order_id', 'customer_name', 'mobile', 'pincode', 'tracking_number')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    inlines = [OnlineOrderItemInline]
    ordering = ('-created_at',)
