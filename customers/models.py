import re
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator


mobile_validator = RegexValidator(
    regex=r'^(?:\+91|0)?[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number (e.g. 9876543210)."
)

pincode_validator = RegexValidator(
    regex=r'^[1-9][0-9]{5}$',
    message="Enter a valid 6-digit Indian PIN code."
)

gstin_validator = RegexValidator(
    regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
    message="Enter a valid 15-character Indian GSTIN format."
)


class Customer(models.Model):
    customer_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=150, db_index=True)

    mobile = models.CharField(max_length=15, validators=[mobile_validator], db_index=True)
    whatsapp = models.CharField(max_length=15, validators=[mobile_validator], blank=True, null=True)
    email = models.EmailField(blank=True, null=True, db_index=True)

    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    state = models.CharField(max_length=100, default='Gujarat', blank=True, null=True)
    pincode = models.CharField(max_length=10, validators=[pincode_validator], blank=True, null=True)

    gst_number = models.CharField(max_length=15, validators=[gstin_validator], blank=True, null=True, db_index=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="ADMIN ONLY - Initial ledger balance (Decimal)")

    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name', 'mobile']),
            models.Index(fields=['city', 'state']),
        ]

    def __str__(self):
        return f"{self.customer_id} - {self.name} ({self.mobile})"

    def save(self, *args, **kwargs):
        # Auto-generate Customer ID if new
        if not self.pk and not self.customer_id:
            last_c = Customer.objects.all().order_by('id').last()
            if not last_c:
                self.customer_id = 'CUS-000001'
            else:
                next_id = last_c.id + 1
                self.customer_id = f'CUS-{next_id:06d}'

        # Normalize GSTIN uppercase if provided
        if self.gst_number:
            self.gst_number = self.gst_number.strip().upper()

        # Normalize Mobile Number
        if self.mobile:
            self.mobile = re.sub(r'[^\d+]', '', self.mobile.strip())

        if self.whatsapp:
            self.whatsapp = re.sub(r'[^\d+]', '', self.whatsapp.strip())

        super().save(*args, **kwargs)
