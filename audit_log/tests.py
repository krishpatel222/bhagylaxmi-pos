from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from .models import AuditLog
from .services import log_audit


class AuditLogTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_aud', password='password123')
        self.admin_user.profile.role = UserProfile.ROLE_ADMIN
        self.admin_user.profile.save()

        self.cashier_user = User.objects.create_user(username='cashier_aud', password='password123')

        self.client = Client()

    def test_01_log_audit_helper_creates_immutable_log(self):
        log = log_audit(
            user=self.admin_user,
            action=AuditLog.ACTION_CREATE,
            model_name='Product',
            object_id='PRD-001',
            description='Created new product Test Item'
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.model_name, 'Product')
        self.assertEqual(log.object_id, 'PRD-001')

    def test_02_admin_can_view_audit_logs(self):
        log_audit(user=self.admin_user, action=AuditLog.ACTION_LOGIN, model_name='User', description='Logged in')
        self.client.login(username='admin_aud', password='password123')
        res = self.client.get(reverse('audit_log:list'))
        self.assertEqual(res.status_code, 200)

    def test_03_cashier_cannot_view_audit_logs(self):
        self.client.login(username='cashier_aud', password='password123')
        res = self.client.get(reverse('audit_log:list'))
        self.assertEqual(res.status_code, 403)
