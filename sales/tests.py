from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile
from categories.models import Category
from products.models import Product
from customers.models import Customer
from inventory.models import InventoryTransaction
from sales.models import Sale, SaleItem


class SalesAndPOSTestCase(TestCase):
    def setUp(self):
        # Create Admin User
        self.admin_user = User.objects.create_user(username='admin_pos', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        # Create Cashier 1 User
        self.cashier_1 = User.objects.create_user(username='cashier_one', password='password123')
        self.cashier_1.profile.role = UserProfile.ROLE_CASHIER
        self.cashier_1.profile.save()

        # Create Cashier 2 User
        self.cashier_2 = User.objects.create_user(username='cashier_two', password='password123')
        self.cashier_2.profile.role = UserProfile.ROLE_CASHIER
        self.cashier_2.profile.save()

        # Category
        self.category = Category.objects.create(name="Groceries", slug="groceries")

        # Test Products
        self.product_a = Product.objects.create(
            name="Sugar 1kg",
            sku="SUG-1KG",
            category=self.category,
            purchase_price=Decimal('40.00'),
            selling_price=Decimal('50.00'),
            mrp=Decimal('55.00'),
            gst_rate=Decimal('5.00'),
            opening_stock=Decimal('10.00'),
            current_stock=Decimal('10.00'),
            minimum_stock=Decimal('2.00'),
            unit="KG",
            is_active=True
        )

        self.product_b = Product.objects.create(
            name="Tea 500g",
            sku="TEA-500G",
            category=self.category,
            purchase_price=Decimal('150.00'),
            selling_price=Decimal('200.00'),
            mrp=Decimal('220.00'),
            gst_rate=Decimal('12.00'),
            opening_stock=Decimal('5.00'),
            current_stock=Decimal('5.00'),
            minimum_stock=Decimal('1.00'),
            unit="PKT",
            is_active=True
        )

        # Customer
        self.customer = Customer.objects.create(
            name="Jigneshbhai Patel",
            mobile="9876543210",
            city="Visnagar",
            opening_balance=Decimal('1000.00')
        )

        self.client = Client()

    def test_01_sale_and_id_generation(self):
        s1 = Sale.objects.create(grand_total=Decimal('100.00'), created_by=self.admin_user)
        s2 = Sale.objects.create(grand_total=Decimal('200.00'), created_by=self.cashier_1)
        self.assertEqual(s1.sale_id, "SAL-000001")
        self.assertEqual(s2.sale_id, "SAL-000002")

    def test_02_product_search_json_excludes_purchase_price(self):
        self.client.login(username='cashier_one', password='password123')
        response = self.client.get(reverse('sales:product_search_json') + '?q=Sugar')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['products']), 1)
        prod = data['products'][0]
        self.assertEqual(prod['name'], "Sugar 1kg")
        self.assertNotIn('purchase_price', prod)
        self.assertIn('selling_price', prod)

    def test_03_successful_cash_checkout_and_single_stock_reduction(self):
        self.client.login(username='cashier_one', password='password123')
        payload = {
            'customer_id': self.customer.id,
            'items': [
                {'product_id': self.product_a.id, 'quantity': 3, 'discount': 0}
            ],
            'overall_discount': 0,
            'payment_method': 'CASH'
        }

        response = self.client.post(
            reverse('sales:checkout'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data['success'])

        # Verify Sale Record
        sale = Sale.objects.get(pk=res_data['sale_pk'])
        self.assertEqual(sale.customer, self.customer)
        self.assertEqual(sale.payment_status, 'PAID')
        self.assertEqual(sale.created_by, self.cashier_1)

        # Verify Stock Reduction
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.current_stock, Decimal('7.00'))  # 10 - 3 = 7

        # Verify InventoryTransaction Record
        txs = InventoryTransaction.objects.filter(product=self.product_a, transaction_type='SALE_OUT')
        self.assertEqual(txs.count(), 1)
        tx = txs.first()
        self.assertEqual(tx.quantity, Decimal('3.00'))
        self.assertEqual(tx.previous_stock, Decimal('10.00'))
        self.assertEqual(tx.new_stock, Decimal('7.00'))

    def test_04_critical_atomic_rollback_on_insufficient_stock(self):
        """
        CRITICAL ATOMIC TEST:
        Product A has 10 stock (request 2).
        Product B has 5 stock (attempt request 10 - INSUFFICIENT).
        Result: Sale and SaleItems must NOT be created, and Product A stock must NOT decrease.
        """
        self.client.login(username='cashier_one', password='password123')
        payload = {
            'customer_id': self.customer.id,
            'items': [
                {'product_id': self.product_a.id, 'quantity': 2, 'discount': 0},
                {'product_id': self.product_b.id, 'quantity': 10, 'discount': 0}  # Stock is only 5!
            ],
            'payment_method': 'CASH'
        }

        response = self.client.post(
            reverse('sales:checkout'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

        # Verify No Sale created
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(SaleItem.objects.count(), 0)

        # Verify Stocks remain untouched
        self.product_a.refresh_from_db()
        self.product_b.refresh_from_db()
        self.assertEqual(self.product_a.current_stock, Decimal('10.00'))
        self.assertEqual(self.product_b.current_stock, Decimal('5.00'))

        # Verify No SALE_OUT transactions created
        self.assertEqual(InventoryTransaction.objects.filter(transaction_type='SALE_OUT').count(), 0)

    def test_05_walk_in_customer_checkout(self):
        self.client.login(username='cashier_one', password='password123')
        payload = {
            'customer_id': None,  # Walk-in
            'items': [
                {'product_id': self.product_a.id, 'quantity': 1, 'discount': 0}
            ],
            'payment_method': 'CASH'
        }
        response = self.client.post(reverse('sales:checkout'), data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        sale = Sale.objects.first()
        self.assertIsNone(sale.customer)

    def test_06_mixed_payment_validation(self):
        self.client.login(username='cashier_one', password='password123')
        payload = {
            'customer_id': self.customer.id,
            'items': [{'product_id': self.product_a.id, 'quantity': 1, 'discount': 0}],
            'payment_method': 'MIXED',
            'cash_amount': 20.00,
            'upi_amount': 20.00,
            'credit_amount': 12.50
        }
        response = self.client.post(reverse('sales:checkout'), data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        sale = Sale.objects.first()
        self.assertEqual(sale.paid_amount, Decimal('40.00'))
        self.assertEqual(sale.pending_amount, Decimal('12.50'))
        self.assertEqual(sale.payment_status, 'PARTIAL')

    def test_07_historical_price_and_gst_snapshot(self):
        self.client.login(username='cashier_one', password='password123')
        payload = {
            'items': [{'product_id': self.product_a.id, 'quantity': 1, 'discount': 0}],
            'payment_method': 'CASH'
        }
        self.client.post(reverse('sales:checkout'), data=payload, content_type='application/json')

        # Change master product price & GST rate
        self.product_a.selling_price = Decimal('999.00')
        self.product_a.gst_rate = Decimal('28.00')
        self.product_a.save()

        item = SaleItem.objects.first()
        self.assertEqual(item.selling_price, Decimal('50.00'))  # Preserved original ₹50
        self.assertEqual(item.gst_rate, Decimal('5.00'))        # Preserved original 5%

    def test_08_completed_sale_immutable(self):
        s = Sale.objects.create(grand_total=Decimal('100.00'), created_by=self.cashier_1)
        self.client.login(username='admin_pos', password='password123')
        
        res_edit = self.client.get(reverse('sales:edit', kwargs={'pk': s.pk}), follow=True)
        self.assertContains(res_edit, "cannot be edited or deleted")

        res_del = self.client.get(reverse('sales:delete', kwargs={'pk': s.pk}), follow=True)
        self.assertContains(res_del, "cannot be edited or deleted")

    def test_09_role_security_cashier_sees_only_own_sales(self):
        s_admin = Sale.objects.create(grand_total=Decimal('100.00'), created_by=self.admin_user)
        s_c1 = Sale.objects.create(grand_total=Decimal('200.00'), created_by=self.cashier_1)
        s_c2 = Sale.objects.create(grand_total=Decimal('300.00'), created_by=self.cashier_2)

        # Cashier 1 Login
        self.client.login(username='cashier_one', password='password123')
        res_c1_list = self.client.get(reverse('sales:list'))
        sales_shown = res_c1_list.context['sales']
        self.assertEqual(len(sales_shown), 1)
        self.assertEqual(sales_shown[0], s_c1)

        # Cashier 1 attempts to access Cashier 2's sale detail -> Forbidden 403
        res_forbidden = self.client.get(reverse('sales:detail', kwargs={'pk': s_c2.pk}))
        self.assertEqual(res_forbidden.status_code, 403)

        # Admin Login -> Admin sees all 3 sales
        self.client.login(username='admin_pos', password='password123')
        res_admin_list = self.client.get(reverse('sales:list'))
        self.assertEqual(len(res_admin_list.context['sales']), 3)

    def test_10_cashier_cannot_see_purchase_price_or_supplier_data(self):
        self.client.login(username='cashier_one', password='password123')
        
        # Supplier List -> Forbidden
        res_supp = self.client.get('/suppliers/')
        self.assertEqual(res_supp.status_code, 403)

        # Purchases List -> Forbidden
        res_purch = self.client.get('/purchases/')
        self.assertEqual(res_purch.status_code, 403)

    def test_11_a4_invoice_rendering(self):
        s_reg = Sale.objects.create(customer=self.customer, grand_total=Decimal('52.50'), created_by=self.cashier_1)
        SaleItem.objects.create(sale=s_reg, product=self.product_a, quantity=Decimal('1.00'), selling_price=Decimal('50.00'), line_total=Decimal('52.50'))

        s_walkin = Sale.objects.create(customer=None, grand_total=Decimal('52.50'), created_by=self.cashier_1)
        SaleItem.objects.create(sale=s_walkin, product=self.product_a, quantity=Decimal('1.00'), selling_price=Decimal('50.00'), line_total=Decimal('52.50'))

        self.client.login(username='cashier_one', password='password123')

        # Registered Customer Invoice
        res1 = self.client.get(reverse('sales:invoice', kwargs={'pk': s_reg.pk}))
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, "Jigneshbhai Patel")
        self.assertContains(res1, "TAX INVOICE")

        # Walk-in Customer Invoice
        res2 = self.client.get(reverse('sales:invoice', kwargs={'pk': s_walkin.pk}))
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "Walk-in Customer")

    def test_12_a4_invoice_privacy_no_cost_or_supplier_leakage(self):
        s = Sale.objects.create(customer=self.customer, grand_total=Decimal('52.50'), created_by=self.cashier_1)
        SaleItem.objects.create(sale=s, product=self.product_a, quantity=Decimal('1.00'), selling_price=Decimal('50.00'), line_total=Decimal('52.50'))

        self.client.login(username='cashier_one', password='password123')
        res = self.client.get(reverse('sales:invoice', kwargs={'pk': s.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, "40.00")  # Purchase price of Product A is ₹40.00
        self.assertNotContains(res, "purchase_price")
        self.assertNotContains(res, "profit")

    def test_13_thermal_80mm_receipt_rendering(self):
        s = Sale.objects.create(customer=self.customer, grand_total=Decimal('52.50'), created_by=self.cashier_1)
        self.client.login(username='cashier_one', password='password123')
        res = self.client.get(reverse('sales:receipt', kwargs={'pk': s.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "POS BILL RECEIPT")

    def test_14_sales_search_and_filters(self):
        s1 = Sale.objects.create(customer=self.customer, grand_total=Decimal('100.00'), payment_method='CASH', payment_status='PAID', created_by=self.admin_user)
        s2 = Sale.objects.create(customer=None, grand_total=Decimal('200.00'), payment_method='UPI', payment_status='PENDING', created_by=self.cashier_1)

        self.client.login(username='admin_pos', password='password123')

        # Filter by status = PENDING
        res_pending = self.client.get(reverse('sales:list') + '?status=PENDING')
        self.assertEqual(len(res_pending.context['sales']), 1)
        self.assertEqual(res_pending.context['sales'][0], s2)

        # Filter by method = CASH
        res_cash = self.client.get(reverse('sales:list') + '?method=CASH')
        self.assertEqual(len(res_cash.context['sales']), 1)
        self.assertEqual(res_cash.context['sales'][0], s1)

    def test_15_customer_purchase_history_in_customer_detail(self):
        Sale.objects.create(customer=self.customer, grand_total=Decimal('150.00'), created_by=self.cashier_1)
        self.client.login(username='cashier_one', password='password123')

        res = self.client.get(reverse('customers:detail', kwargs={'pk': self.customer.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "SAL-000001")
        self.assertContains(res, "Purchase Receipts & Invoice History")
