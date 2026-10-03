from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'model_name', 'object_id', 'ip_address')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('description', 'object_id', 'user__username')
    readonly_fields = ('created_at', 'user', 'action', 'model_name', 'object_id', 'description', 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
