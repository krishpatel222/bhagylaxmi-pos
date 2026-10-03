from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from sales.models import Sale
from customers.models import Customer
from products.models import Product


class SalesReturn(models.Model):
    return_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')
    
    return_date = models.DateTimeField(default=timezone.now, db_index=True)
    reason = models.CharField(max_length=255)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales_returns')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['return_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.return_id} (Sale: {self.sale.sale_id}) - ₹{self.refund_amount}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.return_id:
            last_ret = SalesReturn.objects.all().order_by('id').last()
            if not last_ret:
                self.return_id = 'RET-000001'
            else:
                next_id = last_ret.id + 1
                self.return_id = f'RET-{next_id:06d}'
        super().save(*args, **kwargs)


class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='return_items')
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.sales_return.return_id} | {self.product.name} x {self.quantity} = ₹{self.refund_amount}"
