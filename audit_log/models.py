from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_STOCK_CHANGE = 'STOCK_CHANGE'
    ACTION_SALE = 'SALE'
    ACTION_PURCHASE = 'PURCHASE'
    ACTION_RETURN = 'RETURN'
    ACTION_EXPENSE = 'EXPENSE'
    ACTION_ORDER_STATUS_CHANGE = 'ORDER_STATUS_CHANGE'
    ACTION_SETTINGS_CHANGE = 'SETTINGS_CHANGE'
    ACTION_USER_CHANGE = 'USER_CHANGE'

    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_STOCK_CHANGE, 'Stock Change'),
        (ACTION_SALE, 'Sale'),
        (ACTION_PURCHASE, 'Purchase'),
        (ACTION_RETURN, 'Return'),
        (ACTION_EXPENSE, 'Expense'),
        (ACTION_ORDER_STATUS_CHANGE, 'Order Status Change'),
        (ACTION_SETTINGS_CHANGE, 'Settings Change'),
        (ACTION_USER_CHANGE, 'User Change'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.action} ({self.model_name})"
