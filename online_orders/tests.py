from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from accounts.models import UserProfile
from categories.models import Category
from products.models import Product
from customers.models import Customer
from inventory.models import InventoryTransaction
from online_orders.models import OnlineOrder, OnlineOrderItem


class OnlineOrdersTestCase(TestCase):
    def setUp(self):
        # Create Admin User
        self.admin_user = User.objects.create_user(username='admin_oo', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        # Create Cashier User
        self.cashier_user = User.objects.create_user(username='cashier_oo', password='password123')
        self.cashier_user.profile.role = UserProfile.ROLE_CASHIER
        self.cashier_user.profile.save()

        # Category
        self.category = Category.objects.create(name="Groceries", slug="groceries")

        # Test Product
        self.product = Product.objects.create(
            name="Basmati Rice 5kg",
            sku="RICE-5KG",
            category=self.category,
            purchase_price=Decimal('350.00'),
            selling_price=Decimal('450.00'),
            mrp=Decimal('500.00'),
            gst_rate=Decimal('5.00'),
            opening_stock=Decimal('50.00'),
            current_stock=Decimal('50.00'),
            minimum_stock=Decimal('5.00'),
            unit="KG",
            is_active=True
        )

        # Customer
        self.customer = Customer.objects.create(
            name="Rameshbhai Patel",
            mobile="9876543210",
            city="Visnagar",
            opening_balance=Decimal('0.00')
        )

        self.client = Client()

    def test_01_admin_can_create_order_and_id_generation(self):
        o1 = OnlineOrder.objects.create(
            customer_name="Customer 1", mobile="9876543210", full_address="Add 1",
            city="Visnagar", pincode="384315", order_amount=Decimal('500.00'), created_by=self.admin_user
        )
        o2 = OnlineOrder.objects.create(
            customer_name="Customer 2", mobile="9876543211", full_address="Add 2",
            city="Mehsana", pincode="384001", order_amount=Decimal('1000.00'), created_by=self.admin_user
        )
        self.assertEqual(o1.order_id, "ORD-000001")
        self.assertEqual(o2.order_id, "ORD-000002")

    def test_02_multiple_products_and_totals_calculation(self):
        order = OnlineOrder.objects.create(
            customer_name="Test Recipient", mobile="9876543210", full_address="123 Main St",
            city="Visnagar", pincode="384315", order_amount=Decimal('900.00'), payment_received=Decimal('400.00'),
            created_by=self.admin_user
        )
        OnlineOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('2.00'), selling_price=Decimal('450.00'), line_total=Decimal('900.00'))

        self.assertEqual(order.order_amount, Decimal('900.00'))
        self.assertEqual(order.payment_received, Decimal('400.00'))
        self.assertEqual(order.pending_amount, Decimal('500.00'))

    def test_03_payment_statuses(self):
        # PAID
        o_paid = OnlineOrder.objects.create(customer_name="C1", mobile="9876543210", full_address="A", city="C", pincode="384315", order_amount=Decimal('500.00'), payment_received=Decimal('500.00'), payment_status='PAID')
        self.assertEqual(o_paid.payment_status, 'PAID')

        # PARTIAL
        o_partial = OnlineOrder.objects.create(customer_name="C2", mobile="9876543210", full_address="A", city="C", pincode="384315", order_amount=Decimal('500.00'), payment_received=Decimal('200.00'), payment_status='PARTIAL')
        self.assertEqual(o_partial.payment_status, 'PARTIAL')

        # COD
        o_cod = OnlineOrder.objects.create(customer_name="C3", mobile="9876543210", full_address="A", city="C", pincode="384315", order_amount=Decimal('500.00'), payment_received=Decimal('0.00'), payment_status='COD')
        self.assertEqual(o_cod.payment_status, 'COD')

    def test_04_order_search_and_filters(self):
        o1 = OnlineOrder.objects.create(customer_name="Vijay Patel", mobile="9876543210", full_address="Add 1", city="Visnagar", pincode="384315", status='NEW', tracking_number="AWB1001")
        o2 = OnlineOrder.objects.create(customer_name="Sanjay Shah", mobile="9123456789", full_address="Add 2", city="Mehsana", pincode="384001", status='DISPATCHED', tracking_number="AWB2002")

        self.client.login(username='admin_oo', password='password123')

        # Search by tracking number
        res_search = self.client.get(reverse('online_orders:list') + '?q=AWB1001')
        self.assertEqual(len(res_search.context['orders']), 1)
        self.assertEqual(res_search.context['orders'][0], o1)

        # Filter by status DISPATCHED
        res_status = self.client.get(reverse('online_orders:list') + '?status=DISPATCHED')
        self.assertEqual(len(res_status.context['orders']), 1)
        self.assertEqual(res_status.context['orders'][0], o2)

    def test_05_status_transition_to_dispatched_sets_date_and_stock_out(self):
        order = OnlineOrder.objects.create(
            customer_name="Prakashbhai", mobile="9876543210", full_address="Visnagar Road",
            city="Visnagar", pincode="384315", status='PACKED'
        )
        OnlineOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('5.00'), selling_price=Decimal('450.00'), line_total=Decimal('2250.00'))

        self.client.login(username='admin_oo', password='password123')
        response = self.client.post(reverse('online_orders:status_change', kwargs={'pk': order.pk}), {
            'status': 'DISPATCHED',
            'courier_name': 'Delhivery',
            'tracking_number': 'DEL123456789'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'DISPATCHED')
        self.assertIsNotNone(order.dispatch_date)
        self.assertEqual(order.courier_name, 'Delhivery')
        self.assertEqual(order.tracking_number, 'DEL123456789')

        # Check stock reduction (50 - 5 = 45)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('45.00'))

        # Check InventoryTransaction created with SALE_OUT
        txs = InventoryTransaction.objects.filter(product=self.product, transaction_type='SALE_OUT', reference_type='ONLINE_ORDER')
        self.assertEqual(txs.count(), 1)

    def test_06_printing_shipping_label_does_not_change_order_status(self):
        order = OnlineOrder.objects.create(
            customer_name="Prakashbhai", mobile="9876543210", full_address="Visnagar Road",
            city="Visnagar", pincode="384315", status='PACKED'
        )
        self.client.login(username='admin_oo', password='password123')
        res = self.client.get(reverse('online_orders:shipping_label', kwargs={'pk': order.pk}))
        self.assertEqual(res.status_code, 200)

        # Status must remain PACKED
        order.refresh_from_db()
        self.assertEqual(order.status, 'PACKED')

    def test_07_shipping_label_privacy_and_security_audit(self):
        """
        CRITICAL SECURITY AUDIT TEST:
        Shipping label MUST contain: Customer Name, Address, Mobile, PIN, Order ID, Courier/Tracking, Content description.
        Shipping label MUST NOT contain: Order amount (₹3000), payment received, pending amount, payment status, purchase price, profit, supplier, internal notes.
        """
        order = OnlineOrder.objects.create(
            customer_name="Secret Financial Customer", mobile="9876543210", full_address="Sector 5, Nutan Road",
            city="Visnagar", state="Gujarat", pincode="384315", order_amount=Decimal('3000.00'), payment_received=Decimal('1000.00'),
            pending_amount=Decimal('2000.00'), payment_status='PARTIAL', courier_name='India Post', tracking_number='IP987654',
            notes="INTERNAL CONFIDENTIAL NOTE FOR ADMIN ONLY"
        )
        OnlineOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('2.00'), selling_price=Decimal('450.00'), line_total=Decimal('900.00'))

        self.client.login(username='admin_oo', password='password123')
        response = self.client.get(reverse('online_orders:shipping_label', kwargs={'pk': order.pk}))
        self.assertEqual(response.status_code, 200)

        # Must Contain:
        self.assertContains(response, "Secret Financial Customer")
        self.assertContains(response, "Sector 5, Nutan Road")
        self.assertContains(response, "9876543210")
        self.assertContains(response, "384315")
        self.assertContains(response, order.order_id)
        self.assertContains(response, "India Post")
        self.assertContains(response, "IP987654")
        self.assertContains(response, "Basmati Rice 5kg")

        # MUST NOT CONTAIN (Financial & Internal Privacy Mandate):
        self.assertNotContains(response, "3000.00")
        self.assertNotContains(response, "1000.00")
        self.assertNotContains(response, "2000.00")
        self.assertNotContains(response, "PARTIAL")
        self.assertNotContains(response, "350.00")  # Purchase price of product is ₹350
        self.assertNotContains(response, "INTERNAL CONFIDENTIAL NOTE")
        self.assertNotContains(response, "order_amount")

    def test_08_dispatch_dashboard_queue(self):
        o1 = OnlineOrder.objects.create(customer_name="C1", mobile="9876543210", full_address="A", city="Visnagar", pincode="384315", status='PACKED')
        o2 = OnlineOrder.objects.create(customer_name="C2", mobile="9876543210", full_address="A", city="Visnagar", pincode="384315", status='DELIVERED')

        self.client.login(username='admin_oo', password='password123')
        res = self.client.get(reverse('online_orders:dispatch'))
        self.assertEqual(res.status_code, 200)
        orders_in_queue = res.context['orders']
        self.assertIn(o1, orders_in_queue)
        self.assertNotIn(o2, orders_in_queue)

    def test_09_existing_pos_sales_inventory_dashboard_functional(self):
        self.client.login(username='admin_oo', password='password123')

        # Check POS billing screen
        res_pos = self.client.get(reverse('sales:pos'))
        self.assertEqual(res_pos.status_code, 200)

        # Check Sales list
        res_sales = self.client.get(reverse('sales:list'))
        self.assertEqual(res_sales.status_code, 200)

        # Check Dashboard
        res_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(res_dash.status_code, 200)
