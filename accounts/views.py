from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import UserProfile
from .forms import LoginForm, UserCreationFormCustom, UserEditFormCustom
from .decorators import admin_required


def user_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.is_cashier:
            return redirect('pos_billing')
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            remember_me = form.cleaned_data.get('remember_me')
            
            login(request, user)
            
            if not remember_me:
                # Session expires on browser close
                request.session.set_expiry(0)
            else:
                # 30 days session
                request.session.set_expiry(30 * 24 * 3600)
                
            messages.success(request, f"Welcome back, {user.username}! / સ્વાગત છે, {user.username}!")
            
            # Redirect based on role
            if hasattr(user, 'profile') and user.profile.is_cashier:
                return redirect('pos_billing')
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again. / ખોટો યુઝરનેમ અથવા પાસવર્ડ.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully. / સફળતાપૂર્વક લોગ આઉટ થયા.")
    return redirect('login')


@admin_required
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    return render(request, 'accounts/user_list.html', {'users': users})


@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreationFormCustom(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User account for '{user.username}' created successfully!")
            return redirect('user_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationFormCustom()

    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create New Staff Account'})


@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditFormCustom(request.POST, instance=user_obj)
        if form.is_valid():
            new_role = form.cleaned_data.get('role')
            new_active = form.cleaned_data.get('is_active')

            # Prevent demoting/deactivating the last active admin
            if user_obj.profile.is_admin and (new_role != UserProfile.ROLE_ADMIN or not new_active):
                active_admins = User.objects.filter(is_active=True, profile__role=UserProfile.ROLE_ADMIN).count()
                if active_admins <= 1:
                    messages.error(request, "Cannot demote or deactivate the last active Admin account!")
                    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Edit User: {user_obj.username}'})

            form.save()
            messages.success(request, f"User '{user_obj.username}' updated successfully!")
            return redirect('user_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserEditFormCustom(instance=user_obj)

    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Edit User: {user_obj.username}'})


@admin_required
def user_toggle_status(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own account!")
    elif user_obj.profile.is_admin and user_obj.is_active:
        active_admins = User.objects.filter(is_active=True, profile__role=UserProfile.ROLE_ADMIN).count()
        if active_admins <= 1:
            messages.error(request, "Cannot deactivate the last active Admin account!")
        else:
            user_obj.is_active = False
            user_obj.save()
            messages.success(request, f"User '{user_obj.username}' has been deactivated.")
    else:
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        status_str = "activated" if user_obj.is_active else "deactivated"
        messages.success(request, f"User '{user_obj.username}' has been {status_str}.")
    return redirect('user_list')


@admin_required
def user_reset_password(request, pk):
    """
    Admin-only safe password reset view.
    """
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        if not new_password or len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
        else:
            user_obj.set_password(new_password)
            user_obj.save()
            messages.success(request, f"Password for '{user_obj.username}' reset successfully!")
            return redirect('user_list')

    return render(request, 'accounts/user_password_reset.html', {'user_obj': user_obj})

