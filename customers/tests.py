from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile
from customers.models import Customer
from customers.forms import CustomerForm, CashierCustomerForm


class CustomerModelAndSecurityTest(TestCase):
    def setUp(self):
        # Create Admin User
        self.admin_user = User.objects.create_user(username='admin_test', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        # Create Cashier User
        self.cashier_user = User.objects.create_user(username='cashier_test', password='password123')
        self.cashier_user.profile.role = UserProfile.ROLE_CASHIER
        self.cashier_user.profile.save()

        self.client = Client()

    def test_01_customer_creation(self):
        c = Customer.objects.create(
            name="Rameshbhai Patel",
            mobile="9876543210",
            city="Visnagar",
            opening_balance=Decimal('500.00')
        )
        self.assertEqual(c.name, "Rameshbhai Patel")
        self.assertEqual(c.mobile, "9876543210")
        self.assertEqual(c.opening_balance, Decimal('500.00'))
        self.assertTrue(c.is_active)

    def test_02_customer_id_generation(self):
        c1 = Customer.objects.create(name="Customer 1", mobile="9876543210")
        c2 = Customer.objects.create(name="Customer 2", mobile="9876543211")
        self.assertEqual(c1.customer_id, "CUS-000001")
        self.assertEqual(c2.customer_id, "CUS-000002")

    def test_03_customer_id_uniqueness(self):
        c1 = Customer.objects.create(name="Customer 1", mobile="9876543210")
        c2 = Customer.objects.create(name="Customer 2", mobile="9876543211")
        self.assertNotEqual(c1.customer_id, c2.customer_id)

    def test_04_customer_editing(self):
        c = Customer.objects.create(name="Old Name", mobile="9876543210")
        c.name = "New Name"
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.name, "New Name")
        self.assertEqual(c.customer_id, "CUS-000001")  # Remains stable

    def test_05_customer_deletion(self):
        c = Customer.objects.create(name="Delete Me", mobile="9876543210")
        cid = c.id
        c.delete()
        self.assertFalse(Customer.objects.filter(id=cid).exists())

    def test_06_customer_activation_deactivation(self):
        c = Customer.objects.create(name="Active Customer", mobile="9876543210")
        c.is_active = False
        c.save()
        self.assertFalse(Customer.objects.get(pk=c.pk).is_active)

    def test_07_mobile_validation(self):
        form = CustomerForm(data={'name': 'Test', 'mobile': '12345'})
        self.assertFalse(form.is_valid())
        self.assertIn('mobile', form.errors)

        valid_form = CustomerForm(data={'name': 'Test', 'mobile': '9876543210', 'opening_balance': '0'})
        self.assertTrue(valid_form.is_valid())

    def test_08_whatsapp_validation(self):
        c = Customer(name="Test", mobile="9876543210", whatsapp="invalid_wa")
        with self.assertRaises(Exception):
            c.full_clean()

    def test_09_email_validation(self):
        form = CustomerForm(data={'name': 'Test', 'mobile': '9876543210', 'email': 'not-an-email'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_10_pincode_validation(self):
        form = CustomerForm(data={'name': 'Test', 'mobile': '9876543210', 'pincode': '3843150'})
        self.assertFalse(form.is_valid())
        self.assertIn('pincode', form.errors)

    def test_11_gst_validation(self):
        form = CustomerForm(data={'name': 'Test', 'mobile': '9876543210', 'gst_number': 'INVALID_GST'})
        self.assertFalse(form.is_valid())
        self.assertIn('gst_number', form.errors)

    def test_12_negative_opening_balance_rejection(self):
        form = CustomerForm(data={'name': 'Test', 'mobile': '9876543210', 'opening_balance': '-100.00'})
        self.assertFalse(form.is_valid())
        self.assertIn('opening_balance', form.errors)

    def test_13_search(self):
        Customer.objects.create(name="Patel Electronics", mobile="9876543210", city="Visnagar")
        Customer.objects.create(name="Shah General Store", mobile="9123456789", city="Mehsana")

        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('customers:list') + '?q=Visnagar')
        self.assertEqual(len(response.context['customers']), 1)
        self.assertEqual(response.context['customers'][0].name, "Patel Electronics")

    def test_14_filters(self):
        Customer.objects.create(name="Active C", mobile="9876543210", is_active=True)
        Customer.objects.create(name="Inactive C", mobile="9876543211", is_active=False)

        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('customers:list') + '?status=inactive')
        self.assertEqual(len(response.context['customers']), 1)
        self.assertEqual(response.context['customers'][0].name, "Inactive C")

    def test_15_pagination(self):
        for i in range(30):
            Customer.objects.create(name=f"Customer {i}", mobile=f"98765{i:05d}")

        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('customers:list'))
        self.assertEqual(len(response.context['customers']), 25)

    def test_16_admin_access(self):
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('customers:list'))
        self.assertEqual(response.status_code, 200)

    def test_17_cashier_access(self):
        self.client.login(username='cashier_test', password='password123')
        response = self.client.get(reverse('customers:list'))
        self.assertEqual(response.status_code, 200)

    def test_18_cashier_form_excludes_opening_balance(self):
        form = CashierCustomerForm()
        self.assertNotIn('opening_balance', form.fields)

    def test_19_cashier_cannot_modify_opening_balance_backend_security(self):
        """
        SECURITY TEST:
        Cashier submits opening_balance in POST data.
        Backend MUST ignore/exclude opening_balance.
        """
        self.client.login(username='cashier_test', password='password123')
        response = self.client.post(reverse('customers:add'), {
            'name': 'Hacked Customer',
            'mobile': '9876543210',
            'opening_balance': '999999.99'  # Malicious attempt
        })
        self.assertEqual(response.status_code, 302)
        created_c = Customer.objects.get(name='Hacked Customer')
        self.assertEqual(created_c.opening_balance, Decimal('0.00'))  # Remained 0.00!

    def test_20_cashier_cannot_see_financial_data(self):
        c = Customer.objects.create(name="Rich Customer", mobile="9876543210", opening_balance=Decimal('25000.00'))
        self.client.login(username='cashier_test', password='password123')
        response = self.client.get(reverse('customers:detail', kwargs={'pk': c.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Financial Ledger Summary')
        self.assertNotContains(response, '25000.00')

    def test_21_admin_can_see_financial_data(self):
        c = Customer.objects.create(name="Rich Customer", mobile="9876543210", opening_balance=Decimal('25000.00'))
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('customers:detail', kwargs={'pk': c.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financial Ledger Summary')
        self.assertContains(response, '25000.00')

    def test_22_duplicate_mobile_warning(self):
        Customer.objects.create(name="First Customer", mobile="9876543210")
        self.client.login(username='admin_test', password='password123')
        response = self.client.post(reverse('customers:add'), {
            'name': 'Second Customer',
            'mobile': '9876543210',
            'opening_balance': '0.00'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has mobile number")

    def test_23_customer_selector(self):
        c = Customer.objects.create(name="Selector Customer", mobile="9876543210", city="Visnagar")
        self.client.login(username='cashier_test', password='password123')
        response = self.client.get(reverse('customers:search_json') + '?q=Selector')
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(len(json_data['customers']), 1)
        self.assertEqual(json_data['customers'][0]['name'], "Selector Customer")
        self.assertNotIn('opening_balance', json_data['customers'][0])

    def test_24_existing_modules_functional(self):
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
