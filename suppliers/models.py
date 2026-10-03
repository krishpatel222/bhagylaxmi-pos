import re
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator


# Indian Mobile Number Validator (10 digits, optionally starting with +91 or 0)
mobile_validator = RegexValidator(
    regex=r'^(?:\+91|0)?[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number (e.g. 9876543210)."
)

# Indian PIN Code Validator (6 digits)
pincode_validator = RegexValidator(
    regex=r'^[1-9][0-9]{5}$',
    message="Enter a valid 6-digit Indian PIN code."
)

# Indian GSTIN Validator (15 alphanumeric characters)
gstin_validator = RegexValidator(
    regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
    message="Enter a valid 15-character Indian GSTIN format (e.g. 24AAAAA0000A1Z5)."
)


class Supplier(models.Model):
    supplier_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    company_name = models.CharField(max_length=150, blank=True, null=True, db_index=True)

    mobile = models.CharField(max_length=15, validators=[mobile_validator], db_index=True)
    whatsapp = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    state = models.CharField(max_length=100, default='Gujarat', blank=True, null=True)
    pincode = models.CharField(max_length=10, validators=[pincode_validator], blank=True, null=True)

    gst_number = models.CharField(max_length=15, validators=[gstin_validator], blank=True, null=True, db_index=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Initial ledger balance (Decimal)")

    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name', 'company_name']),
            models.Index(fields=['city', 'state']),
        ]

    def __str__(self):
        if self.company_name:
            return f"{self.supplier_id} - {self.name} ({self.company_name})"
        return f"{self.supplier_id} - {self.name}"

    def save(self, *args, **kwargs):
        # Auto-generate Supplier ID if new
        if not self.pk and not self.supplier_id:
            last_supplier = Supplier.objects.all().order_by('id').last()
            if not last_supplier:
                self.supplier_id = 'SUP-000001'
            else:
                next_id = last_supplier.id + 1
                self.supplier_id = f'SUP-{next_id:06d}'

        # Normalize GSTIN uppercase if provided
        if self.gst_number:
            self.gst_number = self.gst_number.strip().upper()

        # Normalize Mobile Number
        if self.mobile:
            self.mobile = re.sub(r'[^\d+]', '', self.mobile.strip())

        super().save(*args, **kwargs)
