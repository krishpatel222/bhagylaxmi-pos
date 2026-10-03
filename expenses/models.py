from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Expense(models.Model):
    CATEGORY_RENT = 'RENT'
    CATEGORY_ELECTRICITY = 'ELECTRICITY'
    CATEGORY_SALARY = 'SALARY'
    CATEGORY_COURIER = 'COURIER'
    CATEGORY_TRANSPORT = 'TRANSPORT'
    CATEGORY_PACKAGING = 'PACKAGING'
    CATEGORY_MARKETING = 'MARKETING'
    CATEGORY_OTHER = 'OTHER'

    CATEGORY_CHOICES = [
        (CATEGORY_RENT, 'Rent'),
        (CATEGORY_ELECTRICITY, 'Electricity'),
        (CATEGORY_SALARY, 'Salary'),
        (CATEGORY_COURIER, 'Courier'),
        (CATEGORY_TRANSPORT, 'Transport'),
        (CATEGORY_PACKAGING, 'Packaging'),
        (CATEGORY_MARKETING, 'Marketing'),
        (CATEGORY_OTHER, 'Other'),
    ]

    PAYMENT_METHOD_CASH = 'CASH'
    PAYMENT_METHOD_UPI = 'UPI'
    PAYMENT_METHOD_CARD = 'CARD'
    PAYMENT_METHOD_BANK = 'BANK_TRANSFER'
    PAYMENT_METHOD_OTHER = 'OTHER'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CASH, 'Cash'),
        (PAYMENT_METHOD_UPI, 'UPI'),
        (PAYMENT_METHOD_CARD, 'Card'),
        (PAYMENT_METHOD_BANK, 'Bank Transfer'),
        (PAYMENT_METHOD_OTHER, 'Other'),
    ]

    expense_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER, db_index=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=timezone.now, db_index=True)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_CASH)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['expense_id', 'created_at']),
            models.Index(fields=['category', 'expense_date']),
        ]

    def __str__(self):
        return f"{self.expense_id} - {self.get_category_display()} (₹{self.amount})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expense_id:
            last_exp = Expense.objects.all().order_by('id').last()
            if not last_exp:
                self.expense_id = 'EXP-000001'
            else:
                next_id = last_exp.id + 1
                self.expense_id = f'EXP-{next_id:06d}'
        super().save(*args, **kwargs)
