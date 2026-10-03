from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from customers.models import Customer
from products.models import Product


class OnlineOrder(models.Model):
    STATUS_NEW = 'NEW'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_PACKED = 'PACKED'
    STATUS_DISPATCHED = 'DISPATCHED'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_RETURNED = 'RETURNED'

    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_PACKED, 'Packed'),
        (STATUS_DISPATCHED, 'Dispatched'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_RETURNED, 'Returned'),
    ]

    PAYMENT_STATUS_PAID = 'PAID'
    PAYMENT_STATUS_PARTIAL = 'PARTIAL'
    PAYMENT_STATUS_COD = 'COD'
    PAYMENT_STATUS_PENDING = 'PENDING'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PAID, 'Paid'),
        (PAYMENT_STATUS_PARTIAL, 'Partial'),
        (PAYMENT_STATUS_COD, 'Cash On Delivery (COD)'),
        (PAYMENT_STATUS_PENDING, 'Pending'),
    ]

    order_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='online_orders')
    
    customer_name = models.CharField(max_length=150, db_index=True)
    mobile = models.CharField(max_length=15, db_index=True)
    whatsapp = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    full_address = models.TextField()
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, default='Gujarat')
    pincode = models.CharField(max_length=10, db_index=True)

    order_date = models.DateTimeField(default=timezone.now, db_index=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING, db_index=True)

    order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    payment_received = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pending_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    courier_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    dispatch_date = models.DateTimeField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True, help_text="Internal notes only - strictly excluded from shipping label")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_online_orders')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['mobile', 'pincode']),
            models.Index(fields=['tracking_number']),
        ]

    def __str__(self):
        return f"{self.order_id} - {self.customer_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.order_id:
            last_ord = OnlineOrder.objects.all().order_by('id').last()
            if not last_ord:
                self.order_id = 'ORD-000001'
            else:
                next_id = last_ord.id + 1
                self.order_id = f'ORD-{next_id:06d}'

        if self.order_amount is not None and self.payment_received is not None:
            calc_pending = self.order_amount - self.payment_received
            self.pending_amount = max(Decimal('0.00'), calc_pending)

        super().save(*args, **kwargs)


class OnlineOrderItem(models.Model):
    order = models.ForeignKey(OnlineOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='online_order_items')
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.order.order_id} | {self.product.name} x {self.quantity} = ₹{self.line_total}"
