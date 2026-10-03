from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from customers.models import Customer
from products.models import Product


class Sale(models.Model):
    PAYMENT_METHOD_CASH = 'CASH'
    PAYMENT_METHOD_UPI = 'UPI'
    PAYMENT_METHOD_CARD = 'CARD'
    PAYMENT_METHOD_BANK = 'BANK_TRANSFER'
    PAYMENT_METHOD_CREDIT = 'CREDIT'
    PAYMENT_METHOD_MIXED = 'MIXED'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CASH, 'Cash'),
        (PAYMENT_METHOD_UPI, 'UPI'),
        (PAYMENT_METHOD_CARD, 'Card'),
        (PAYMENT_METHOD_BANK, 'Bank Transfer'),
        (PAYMENT_METHOD_CREDIT, 'Credit'),
        (PAYMENT_METHOD_MIXED, 'Mixed Payment'),
    ]

    PAYMENT_STATUS_PAID = 'PAID'
    PAYMENT_STATUS_PARTIAL = 'PARTIAL'
    PAYMENT_STATUS_PENDING = 'PENDING'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PAID, 'Paid'),
        (PAYMENT_STATUS_PARTIAL, 'Partial'),
        (PAYMENT_STATUS_PENDING, 'Pending'),
    ]

    sale_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    sale_date = models.DateTimeField(default=timezone.now, db_index=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_CASH, db_index=True)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pending_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PAID, db_index=True)

    # Mixed Payment Breakdown Fields
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    upi_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    card_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bank_transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sale_id', 'created_at']),
            models.Index(fields=['payment_status', 'created_at']),
        ]

    def __str__(self):
        cust_name = self.customer.name if self.customer else "Walk-in Customer"
        return f"{self.sale_id} - {cust_name} (₹{self.grand_total})"

    @property
    def invoice_number(self):
        return self.sale_id

    @property
    def total_item_count(self):
        return self.items.count()

    def save(self, *args, **kwargs):
        if not self.pk and not self.sale_id:
            last_sale = Sale.objects.all().order_by('id').last()
            if not last_sale:
                self.sale_id = 'SAL-000001'
            else:
                next_id = last_sale.id + 1
                self.sale_id = f'SAL-{next_id:06d}'
        super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Historical selling price snapshot")
    mrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Historical GST rate snapshot")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.sale.sale_id} | {self.product.name} x {self.quantity} = ₹{self.line_total}"
