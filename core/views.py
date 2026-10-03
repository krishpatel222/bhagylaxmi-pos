import datetime
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum, F
from django.apps import apps

from accounts.decorators import admin_required, cashier_or_admin_required


@cashier_or_admin_required
def dashboard(request):
    """
    Main Dashboard View.
    Renders Admin Dashboard for Admins, and Cashier Dashboard for Cashiers.
    Timezone: Asia/Kolkata.
    """
    if hasattr(request.user, 'profile') and request.user.profile.is_cashier:
        return cashier_dashboard(request)

    today = timezone.now().astimezone(timezone.get_current_timezone()).date()
    
    today_sales = 0.00
    today_bills = 0
    today_profit = 0.00
    total_products = 0
    low_stock_count = 0
    pending_payments = 0.00
    today_expenses = 0.00
    pending_online_orders = 0
    
    recent_sales = []
    low_stock_products = []

    # 1. Product & Inventory Stats
    if apps.is_installed('products'):
        try:
            Product = apps.get_model('products', 'Product')
            total_products = Product.objects.filter(is_active=True).count()
            low_stock_qs = Product.objects.filter(is_active=True, current_stock__lte=F('minimum_stock'))
            low_stock_count = low_stock_qs.count()
            low_stock_products = list(low_stock_qs[:5])
        except Exception:
            pass

    # 2. Sales Stats
    if apps.is_installed('sales'):
        try:
            Sale = apps.get_model('sales', 'Sale')
            today_sales_qs = Sale.objects.filter(created_at__date=today)
            today_sales = today_sales_qs.aggregate(total=Sum('grand_total'))['total'] or 0.00
            today_bills = today_sales_qs.count()
            recent_sales = list(Sale.objects.select_related('customer', 'created_by').order_by('-created_at')[:5])
        except Exception:
            pass

    # 3. Customer Ledger & Counts
    total_customers = 0
    active_customers = 0
    inactive_customers = 0
    if apps.is_installed('customers'):
        try:
            Customer = apps.get_model('customers', 'Customer')
            total_customers = Customer.objects.count()
            active_customers = Customer.objects.filter(is_active=True).count()
            inactive_customers = Customer.objects.filter(is_active=False).count()
            pending_payments = Customer.objects.aggregate(total=Sum('opening_balance'))['total'] or 0.00
        except Exception:
            pass

    # 4. Expenses Stats
    if apps.is_installed('expenses'):
        try:
            Expense = apps.get_model('expenses', 'Expense')
            today_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or 0.00
        except Exception:
            pass

    # 5. Online Orders Pending
    if apps.is_installed('online_orders'):
        try:
            OnlineOrder = apps.get_model('online_orders', 'OnlineOrder')
            pending_online_orders = OnlineOrder.objects.filter(status__in=['NEW', 'CONFIRMED', 'PACKED']).count()
        except Exception:
            pass

    total_suppliers = 0
    if apps.is_installed('suppliers'):
        try:
            Supplier = apps.get_model('suppliers', 'Supplier')
            total_suppliers = Supplier.objects.filter(is_active=True).count()
        except Exception:
            pass

    today_purchases_total = 0.00
    pending_supplier_payments = 0.00
    if apps.is_installed('purchases'):
        try:
            Purchase = apps.get_model('purchases', 'Purchase')
            today_purchases_qs = Purchase.objects.filter(created_at__date=today)
            today_purchases_total = today_purchases_qs.aggregate(total=Sum('grand_total'))['total'] or 0.00
            pending_supplier_payments = Purchase.objects.aggregate(total=Sum('pending_amount'))['total'] or 0.00
        except Exception:
            pass

    context = {
        "shop_name": "ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ",
        "shop_address": "જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત",
        "today_date": today,
        "today_sales": today_sales,
        "today_bills": today_bills,
        "today_profit": today_profit,
        "today_purchases_total": today_purchases_total,
        "pending_supplier_payments": pending_supplier_payments,
        "total_products": total_products,
        "total_suppliers": total_suppliers,
        "total_customers": total_customers,
        "active_customers": active_customers,
        "inactive_customers": inactive_customers,
        "low_stock_count": low_stock_count,
        "pending_payments": pending_payments,
        "today_expenses": today_expenses,
        "pending_online_orders": pending_online_orders,
        "recent_sales": recent_sales,
        "low_stock_products": low_stock_products,
    }

    return render(request, "core/dashboard.html", context)


@cashier_or_admin_required
def cashier_dashboard(request):
    """
    Dedicated lightweight Cashier Dashboard.
    Strictly isolated from Admin-only financial metrics (profit, purchase totals, expenses, supplier data).
    Timezone: Asia/Kolkata.
    """
    today = timezone.now().astimezone(timezone.get_current_timezone()).date()

    today_bills = 0
    low_stock_count = 0
    pending_online_orders = 0
    recent_sales = []

    if apps.is_installed('sales'):
        try:
            Sale = apps.get_model('sales', 'Sale')
            today_sales_qs = Sale.objects.filter(created_at__date=today, created_by=request.user)
            today_bills = today_sales_qs.count()
            recent_sales = list(Sale.objects.filter(created_by=request.user).select_related('customer').order_by('-created_at')[:5])
        except Exception:
            pass

    if apps.is_installed('products'):
        try:
            Product = apps.get_model('products', 'Product')
            low_stock_count = Product.objects.filter(is_active=True, current_stock__lte=F('minimum_stock')).count()
        except Exception:
            pass

    if apps.is_installed('online_orders'):
        try:
            OnlineOrder = apps.get_model('online_orders', 'OnlineOrder')
            pending_online_orders = OnlineOrder.objects.filter(status__in=['NEW', 'CONFIRMED', 'PACKED']).count()
        except Exception:
            pass

    context = {
        "shop_name": "ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ",
        "shop_address": "જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત",
        "today_date": today,
        "today_bills": today_bills,
        "low_stock_count": low_stock_count,
        "pending_online_orders": pending_online_orders,
        "recent_sales": recent_sales,
    }
    return render(request, "core/cashier_dashboard.html", context)


@admin_required
def shop_settings_view(request):
    """
    Admin-only Shop Settings management view.
    """
    from .models import ShopSettings
    from .forms import ShopSettingsForm
    from django.contrib import messages

    settings_obj = ShopSettings.get_settings()
    if request.method == 'POST':
        form = ShopSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Shop Settings updated successfully!")
            return redirect('shop_settings')
        else:
            messages.error(request, "Please correct the errors in the settings form.")
    else:
        form = ShopSettingsForm(instance=settings_obj)

    return render(request, "core/shop_settings.html", {'form': form, 'settings': settings_obj})


@cashier_or_admin_required
def pos_billing_placeholder(request):
    """
    POS Billing Terminal View.
    Redirects to sales:pos terminal interface.
    """
    return redirect('sales:pos')


def custom_permission_denied_view(request, exception=None):
    """
    Custom 403 Forbidden page for unauthorized access attempts.
    """
    return render(request, "403.html", status=403)


def custom_page_not_found_view(request, exception=None):
    """
    Custom 404 Page Not Found.
    """
    return render(request, "404.html", status=404)


def custom_server_error_view(request):
    """
    Custom 500 Server Error.
    """
    return render(request, "500.html", status=500)