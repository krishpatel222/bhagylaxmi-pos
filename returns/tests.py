from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from categories.models import Category
from products.models import Product
from sales.models import Sale, SaleItem
from returns.models import SalesReturn, SalesReturnItem


class SalesReturnTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_ret', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            name='Test Mouse', sku='SKU-M001', barcode='8901234567890',
            category=self.category, purchase_price=Decimal('100.00'),
            selling_price=Decimal('200.00'), mrp=Decimal('250.00'),
            opening_stock=Decimal('50.00'), current_stock=Decimal('50.00')
        )

        self.sale = Sale.objects.create(
            subtotal=Decimal('400.00'), grand_total=Decimal('400.00'),
            paid_amount=Decimal('400.00'), created_by=self.admin_user
        )
        self.sale_item = SaleItem.objects.create(
            sale=self.sale, product=self.product, quantity=Decimal('2.00'),
            selling_price=Decimal('200.00'), line_total=Decimal('400.00')
        )

        self.client = Client()

    def test_01_valid_return_restores_stock(self):
        self.client.login(username='admin_ret', password='password123')
        res = self.client.post(reverse('returns:create'), {
            'sale_id': self.sale.sale_id,
            'reason': 'Customer returned 1 defective mouse',
            f'qty_{self.sale_item.id}': '1.00',
        })
        self.assertEqual(res.status_code, 302)
        ret = SalesReturn.objects.first()
        self.assertIsNotNone(ret)
        self.assertEqual(ret.refund_amount, Decimal('200.00'))

        # Stock updated from 50 -> 51
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('51.00'))

    def test_02_cannot_return_more_than_sold_quantity(self):
        self.client.login(username='admin_ret', password='password123')
        res = self.client.post(reverse('returns:create'), {
            'sale_id': self.sale.sale_id,
            'reason': 'Excessive return attempt',
            f'qty_{self.sale_item.id}': '5.00',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Maximum returnable quantity is 2.00.")
