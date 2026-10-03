import csv
from decimal import Decimal
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone

from accounts.decorators import admin_required
from sales.models import Sale, SaleItem
from purchases.models import Purchase, PurchaseItem
from products.models import Product
from expenses.models import Expense
from customers.models import Customer
from suppliers.models import Supplier
from online_orders.models import OnlineOrder
from returns.models import SalesReturn, SalesReturnItem


@admin_required
def reports_dashboard(request):
    """
    Admin-only reports hub.
    """
    return render(request, 'reports/dashboard.html')


@admin_required
def sales_report(request):
    """
    Admin-only Sales Report with date filtering and CSV export.
    """
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    qs = Sale.objects.select_related('customer', 'created_by').all()
    if date_from:
        qs = qs.filter(sale_date__gte=date_from)
    if date_to:
        qs = qs.filter(sale_date__lte=date_to)

    total_bills = qs.count()
    total_sales = qs.aggregate(t=Sum('grand_total'))['t'] or Decimal('0.00')
    total_discount = qs.aggregate(t=Sum('discount'))['t'] or Decimal('0.00')
    total_gst = qs.aggregate(t=Sum('gst_amount'))['t'] or Decimal('0.00')
    total_paid = qs.aggregate(t=Sum('paid_amount'))['t'] or Decimal('0.00')
    total_pending = qs.aggregate(t=Sum('pending_amount'))['t'] or Decimal('0.00')

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Sale ID', 'Date', 'Customer', 'Subtotal', 'Discount', 'GST', 'Grand Total', 'Paid', 'Pending', 'Payment Method'])
        for s in qs:
            c_name = s.customer.name if s.customer else 'Walk-in Customer'
            writer.writerow([s.sale_id, s.sale_date.strftime('%Y-%m-%d %H:%M'), c_name, s.subtotal, s.discount, s.gst_amount, s.grand_total, s.paid_amount, s.pending_amount, s.get_payment_method_display()])
        return response

    context = {
        'sales': qs[:50],
        'total_bills': total_bills,
        'total_sales': total_sales,
        'total_discount': total_discount,
        'total_gst': total_gst,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'reports/sales_report.html', context)


@admin_required
def profit_report(request):
    """
    Admin-only Profit Report calculated from sale item revenue minus product cost price.
    """
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    items_qs = SaleItem.objects.select_related('sale', 'product')
    if date_from:
        items_qs = items_qs.filter(sale__sale_date__gte=date_from)
    if date_to:
        items_qs = items_qs.filter(sale__sale_date__lte=date_to)

    total_revenue = Decimal('0.00')
    total_cost = Decimal('0.00')

    for item in items_qs:
        total_revenue += item.line_total
        cost_unit = getattr(item.product, 'purchase_price', Decimal('0.00')) or Decimal('0.00')
        total_cost += item.quantity * cost_unit

    gross_profit = total_revenue - total_cost

    context = {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'gross_profit': gross_profit,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'reports/profit_report.html', context)


@admin_required
def purchases_report(request):
    """
    Admin-only Purchase Report.
    """
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    qs = Purchase.objects.select_related('supplier', 'created_by').all()
    if date_from:
        qs = qs.filter(purchase_date__gte=date_from)
    if date_to:
        qs = qs.filter(purchase_date__lte=date_to)

    count = qs.count()
    total_amount = qs.aggregate(t=Sum('grand_total'))['t'] or Decimal('0.00')
    paid_amount = qs.aggregate(t=Sum('paid_amount'))['t'] or Decimal('0.00')
    pending_amount = qs.aggregate(t=Sum('pending_amount'))['t'] or Decimal('0.00')

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="purchase_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Purchase ID', 'Invoice No', 'Date', 'Supplier', 'Grand Total', 'Paid', 'Pending'])
        for p in qs:
            writer.writerow([p.purchase_id, p.supplier_invoice_number, p.purchase_date.strftime('%Y-%m-%d'), p.supplier.name, p.grand_total, p.paid_amount, p.pending_amount])
        return response

    context = {
        'purchases': qs[:50],
        'count': count,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'reports/purchases_report.html', context)


@admin_required
def inventory_report(request):
    """
    Admin-only Inventory Stock Valuation & Status Report.
    """
    products = Product.objects.select_related('category', 'brand').all()
    
    total_products = products.count()
    low_stock_products = products.filter(current_stock__lte=F('minimum_stock'))
    out_of_stock_products = products.filter(current_stock__lte=0)

    total_stock_value = Decimal('0.00')
    for p in products:
        cost = p.purchase_price or Decimal('0.00')
        total_stock_value += p.current_stock * cost

    context = {
        'products': products[:100],
        'total_products': total_products,
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock_products.count(),
        'total_stock_value': total_stock_value,
    }
    return render(request, 'reports/inventory_report.html', context)


@admin_required
def expenses_report(request):
    """
    Admin-only Expenses Report by category.
    """
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    qs = Expense.objects.all()
    if date_from:
        qs = qs.filter(expense_date__gte=date_from)
    if date_to:
        qs = qs.filter(expense_date__lte=date_to)

    total_expense = qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    by_category = qs.values('category').annotate(total=Sum('amount'), count=Count('id')).order_by('-total')

    context = {
        'total_expense': total_expense,
        'by_category': by_category,
        'categories': dict(Expense.CATEGORY_CHOICES),
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'reports/expenses_report.html', context)


@admin_required
def customers_report(request):
    """
    Admin-only Customer Ledger Report.
    """
    customers = Customer.objects.all()
    context = {'customers': customers[:50]}
    return render(request, 'reports/customers_report.html', context)


@admin_required
def suppliers_report(request):
    """
    Admin-only Supplier Ledger Report.
    """
    suppliers = Supplier.objects.all()
    context = {'suppliers': suppliers[:50]}
    return render(request, 'reports/suppliers_report.html', context)


@admin_required
def online_orders_report(request):
    """
    Admin-only Online Orders Summary Report.
    """
    orders = OnlineOrder.objects.all()
    total_count = orders.count()
    total_amount = orders.aggregate(t=Sum('order_amount'))['t'] or Decimal('0.00')

    context = {
        'orders': orders[:50],
        'total_count': total_count,
        'total_amount': total_amount,
    }
    return render(request, 'reports/online_orders_report.html', context)


@admin_required
def returns_report(request):
    """
    Admin-only Returns Summary Report.
    """
    returns_qs = SalesReturn.objects.select_related('sale', 'customer').all()
    total_count = returns_qs.count()
    total_refund = returns_qs.aggregate(t=Sum('refund_amount'))['t'] or Decimal('0.00')

    context = {
        'returns': returns_qs[:50],
        'total_count': total_count,
        'total_refund': total_refund,
    }
    return render(request, 'reports/returns_report.html', context)
