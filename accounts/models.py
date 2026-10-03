from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_ADMIN = 'ADMIN'
    ROLE_CASHIER = 'CASHIER'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_CASHIER, 'Cashier'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CASHIER)
    phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.user.is_superuser

    @property
    def is_cashier(self):
        return self.role == self.ROLE_CASHIER and not self.user.is_superuser


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = UserProfile.ROLE_ADMIN if instance.is_superuser else UserProfile.ROLE_CASHIER
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        # Ensure profile exists for users created previously or via createsuperuser
        if hasattr(instance, 'profile'):
            if instance.is_superuser and instance.profile.role != UserProfile.ROLE_ADMIN:
                instance.profile.role = UserProfile.ROLE_ADMIN
                instance.profile.save()
        else:
            role = UserProfile.ROLE_ADMIN if instance.is_superuser else UserProfile.ROLE_CASHIER
            UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
