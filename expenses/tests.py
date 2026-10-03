from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from .models import Expense


class ExpenseTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_exp', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        self.cashier_user = User.objects.create_user(username='cashier_exp', password='password123')

        self.client = Client()

    def test_01_admin_can_create_expense(self):
        self.client.login(username='admin_exp', password='password123')
        res = self.client.post(reverse('expenses:create'), {
            'category': Expense.CATEGORY_ELECTRICITY,
            'description': 'Monthly Shop Electricity Bill',
            'amount': '1500.00',
            'expense_date': '2026-10-01',
            'payment_method': Expense.PAYMENT_METHOD_UPI,
            'notes': 'Paid via PhonePe'
        })
        self.assertEqual(res.status_code, 302)
        exp = Expense.objects.first()
        self.assertIsNotNone(exp)
        self.assertEqual(exp.expense_id, 'EXP-000001')
        self.assertEqual(exp.amount, Decimal('1500.00'))

    def test_02_negative_expense_rejected(self):
        self.client.login(username='admin_exp', password='password123')
        res = self.client.post(reverse('expenses:create'), {
            'category': Expense.CATEGORY_RENT,
            'description': 'Shop Rent',
            'amount': '-500.00',
            'expense_date': '2026-10-01',
            'payment_method': Expense.PAYMENT_METHOD_CASH,
        })
        self.assertEqual(res.status_code, 200)
        self.assertFormError(res.context['form'], 'amount', 'Expense amount must be greater than zero.')

    def test_03_cashier_cannot_access_expenses(self):
        self.client.login(username='cashier_exp', password='password123')
        res_list = self.client.get(reverse('expenses:list'))
        self.assertEqual(res_list.status_code, 403)

        res_create = self.client.get(reverse('expenses:create'))
        self.assertEqual(res_create.status_code, 403)
