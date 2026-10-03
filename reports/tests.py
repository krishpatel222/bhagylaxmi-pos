from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from sales.models import Sale


class ReportsTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_rep', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        self.cashier_user = User.objects.create_user(username='cashier_rep', password='password123')

        self.client = Client()

    def test_01_admin_can_access_reports(self):
        self.client.login(username='admin_rep', password='password123')
        res = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(res.status_code, 200)

        res_sales = self.client.get(reverse('reports:sales'))
        self.assertEqual(res_sales.status_code, 200)

    def test_02_cashier_cannot_access_reports(self):
        self.client.login(username='cashier_rep', password='password123')
        res = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(res.status_code, 403)

        res_sales = self.client.get(reverse('reports:sales'))
        self.assertEqual(res_sales.status_code, 403)

        res_profit = self.client.get(reverse('reports:profit'))
        self.assertEqual(res_profit.status_code, 403)

    def test_03_csv_export_respects_permissions(self):
        self.client.login(username='admin_rep', password='password123')
        res = self.client.get(reverse('reports:sales') + '?export=csv')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
