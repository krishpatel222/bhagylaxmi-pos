from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class InventoryTransaction(models.Model):
    TYPE_PURCHASE_IN = 'PURCHASE_IN'
    TYPE_SALE_OUT = 'SALE_OUT'
    TYPE_SALES_RETURN = 'SALES_RETURN'
    TYPE_PURCHASE_RETURN = 'PURCHASE_RETURN'
    TYPE_ADJUSTMENT_IN = 'ADJUSTMENT_IN'
    TYPE_ADJUSTMENT_OUT = 'ADJUSTMENT_OUT'
    TYPE_DAMAGE = 'DAMAGE'
    TYPE_OPENING_STOCK = 'OPENING_STOCK'

    TRANSACTION_TYPE_CHOICES = [
        (TYPE_PURCHASE_IN, 'Purchase In'),
        (TYPE_SALE_OUT, 'Sale Out'),
        (TYPE_SALES_RETURN, 'Sales Return'),
        (TYPE_PURCHASE_RETURN, 'Purchase Return'),
        (TYPE_ADJUSTMENT_IN, 'Adjustment In'),
        (TYPE_ADJUSTMENT_OUT, 'Adjustment Out'),
        (TYPE_DAMAGE, 'Damage'),
        (TYPE_OPENING_STOCK, 'Opening Stock'),
    ]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='inventory_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, db_index=True)
    
    # DECIMAL FIELDS FOR ACCURATE STOCK MEASUREMENTS
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    previous_stock = models.DecimalField(max_digits=12, decimal_places=2)
    new_stock = models.DecimalField(max_digits=12, decimal_places=2)

    # REFERENCE FIELDS (FOR FUTURE PURCHASE, SALE, RETURN INTEGRATIONS)
    reference_type = models.CharField(max_length=50, blank=True, null=True, help_text="Reference module (e.g. PURCHASE, SALE, ADJUSTMENT)")
    reference_id = models.CharField(max_length=50, blank=True, null=True)

    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='inventory_actions')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.product.name} | {self.get_transaction_type_display()} ({self.quantity}) on {self.created_at.strftime('%d/%m/%Y %H:%M')}"
