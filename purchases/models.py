from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from suppliers.models import Supplier
from products.models import Product


class Purchase(models.Model):
    STATUS_PAID = 'PAID'
    STATUS_PARTIAL = 'PARTIAL'
    STATUS_PENDING = 'PENDING'

    PAYMENT_STATUS_CHOICES = [
        (STATUS_PAID, 'Paid'),
        (STATUS_PARTIAL, 'Partial'),
        (STATUS_PENDING, 'Pending'),
    ]

    purchase_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchases')
    invoice_number = models.CharField(max_length=100, db_index=True, help_text="Supplier's Invoice / Bill Number")
    
    purchase_date = models.DateTimeField(default=timezone.now, db_index=True)

    # MONETARY SUMMARY FIELDS (DECIMAL)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    stock_posted = models.BooleanField(default=False, help_text="Indicates if stock has been posted to inventory")

    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_purchases')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['supplier', 'purchase_date']),
            models.Index(fields=['payment_status', 'stock_posted']),
        ]

    def __str__(self):
        return f"{self.purchase_id} - {self.supplier.name} (Inv: {self.invoice_number})"

    def calculate_payment_status(self):
        paid = Decimal(str(self.paid_amount or 0))
        total = Decimal(str(self.grand_total or 0))
        
        self.pending_amount = max(Decimal('0.00'), total - paid)
        
        if paid >= total and total > 0:
            self.payment_status = self.STATUS_PAID
        elif paid == 0:
            self.payment_status = self.STATUS_PENDING
        else:
            self.payment_status = self.STATUS_PARTIAL

    def save(self, *args, **kwargs):
        # Auto-generate Purchase ID if new
        if not self.pk and not self.purchase_id:
            last_p = Purchase.objects.all().order_by('id').last()
            if not last_p:
                self.purchase_id = 'PUR-000001'
            else:
                next_id = last_p.id + 1
                self.purchase_id = f'PUR-{next_id:06d}'

        self.calculate_payment_status()
        super().save(*args, **kwargs)


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_items')
    
    quantity = models.DecimalField(max_digits=12, decimal_places=2, help_text="Quantity purchased")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="ADMIN ONLY - Unit purchase cost")
    
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_line_total(self):
        qty = Decimal(str(self.quantity or 0))
        price = Decimal(str(self.purchase_price or 0))
        rate = Decimal(str(self.gst_rate or 0))
        disc = Decimal(str(self.discount or 0))

        sub = qty * price
        sub_after_disc = max(Decimal('0.00'), sub - disc)
        self.gst_amount = (sub_after_disc * rate) / Decimal('100.00')
        self.line_total = sub_after_disc + self.gst_amount
        return self.line_total

    def save(self, *args, **kwargs):
        self.calculate_line_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.purchase.purchase_id}"
