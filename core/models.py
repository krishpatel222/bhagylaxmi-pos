from decimal import Decimal
from django.db import models


class ShopSettings(models.Model):
    shop_name = models.CharField(max_length=200, default="ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ")
    address = models.CharField(max_length=255, default="જ્યોતિ હોસ્પિટલની સામે નુતન રોડ")
    city = models.CharField(max_length=100, default="વિસનગર")
    state = models.CharField(max_length=100, default="ગુજરાત")
    pincode = models.CharField(max_length=10, default="384315")
    
    mobile = models.CharField(max_length=20, default="9825000000")
    whatsapp = models.CharField(max_length=20, default="9825000000")
    email = models.EmailField(default="info@bhagyalaxmi.com")
    
    gst_number = models.CharField(max_length=20, default="24AAAAA0000A1Z5")
    logo = models.ImageField(upload_to='shop_logo/', null=True, blank=True)
    
    invoice_prefix = models.CharField(max_length=10, default="SAL-")
    order_prefix = models.CharField(max_length=10, default="ORD-")
    currency = models.CharField(max_length=10, default="₹")
    default_gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Settings"
        verbose_name_plural = "Shop Settings"

    def __str__(self):
        return f"Shop Settings - {self.shop_name}"

    @classmethod
    def get_settings(cls):
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj
