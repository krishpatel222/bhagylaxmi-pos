from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is an ADMIN.
    Raises PermissionDenied (403) if unauthorized.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Ensure user has a profile
        if not hasattr(request.user, 'profile'):
            from accounts.models import UserProfile
            role = UserProfile.ROLE_ADMIN if request.user.is_superuser else UserProfile.ROLE_CASHIER
            UserProfile.objects.get_or_create(user=request.user, defaults={'role': role})

        if request.user.profile.is_admin:
            return view_func(request, *args, **kwargs)
        
        raise PermissionDenied("Access Denied: You do not have permission to access Admin features.")

    return _wrapped_view


def cashier_or_admin_required(view_func):
    """
    Decorator for views accessible by both Cashiers and Admins.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not hasattr(request.user, 'profile'):
            from accounts.models import UserProfile
            role = UserProfile.ROLE_ADMIN if request.user.is_superuser else UserProfile.ROLE_CASHIER
            UserProfile.objects.get_or_create(user=request.user, defaults={'role': role})

        return view_func(request, *args, **kwargs)

    return _wrapped_view
