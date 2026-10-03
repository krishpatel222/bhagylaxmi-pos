from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_id', 'category', 'description', 'amount', 'expense_date', 'payment_method', 'created_by')
    list_filter = ('category', 'payment_method', 'expense_date')
    search_fields = ('expense_id', 'description', 'notes')
    readonly_fields = ('expense_id', 'created_at', 'updated_at')
