from decimal import Decimal
from django.db import models
from categories.models import Category, Brand


class Product(models.Model):
    UNIT_PCS = 'PCS'
    UNIT_BOX = 'BOX'
    UNIT_PACK = 'PACK'
    UNIT_KG = 'KG'
    UNIT_GRAM = 'GRAM'
    UNIT_LITRE = 'LITRE'
    UNIT_METER = 'METER'
    UNIT_PAIR = 'PAIR'
    UNIT_SET = 'SET'
    UNIT_OTHER = 'OTHER'

    UNIT_CHOICES = [
        (UNIT_PCS, 'Pieces (PCS)'),
        (UNIT_BOX, 'Box (BOX)'),
        (UNIT_PACK, 'Pack (PACK)'),
        (UNIT_KG, 'Kilogram (KG)'),
        (UNIT_GRAM, 'Gram (GRAM)'),
        (UNIT_LITRE, 'Litre (LITRE)'),
        (UNIT_METER, 'Meter (METER)'),
        (UNIT_PAIR, 'Pair (PAIR)'),
        (UNIT_SET, 'Set (SET)'),
        (UNIT_OTHER, 'Other'),
    ]

    product_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    gujarati_name = models.CharField(max_length=200, blank=True, null=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, db_index=True)
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True)

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, blank=True, null=True, related_name='products')

    # MONEY FIELDS - Strict DecimalField usage
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="ADMIN ONLY - Private purchase cost")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="GST percentage (e.g., 0, 5, 12, 18, 28)")

    # STOCK FIELDS
    opening_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default=UNIT_PCS)

    image = models.ImageField(upload_to='products/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.gujarati_name:
            return f"{self.product_id} - {self.name} ({self.gujarati_name})"
        return f"{self.product_id} - {self.name}"

    @property
    def is_low_stock(self):
        return Decimal(str(self.current_stock or 0)) <= Decimal(str(self.minimum_stock or 0))

    def save(self, *args, **kwargs):
        # Auto-generate Product ID if new
        if not self.pk and not self.product_id:
            last_product = Product.objects.all().order_by('id').last()
            if not last_product:
                self.product_id = 'PRD-000001'
            else:
                next_id = last_product.id + 1
                self.product_id = f'PRD-{next_id:06d}'
            
            # Initialize current stock from opening stock on creation if current stock is 0
            cur_stock_dec = Decimal(str(self.current_stock or 0))
            open_stock_dec = Decimal(str(self.opening_stock or 0))
            if cur_stock_dec == 0 and open_stock_dec > 0:
                self.current_stock = open_stock_dec

        super().save(*args, **kwargs)
