from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from accounts.decorators import admin_required
from products.models import Product
from categories.models import Category, Brand
from .models import InventoryTransaction
from .forms import StockAdjustmentForm
from .services import change_stock


@admin_required
def inventory_dashboard(request):
    """
    Main Admin Inventory Dashboard.
    Provides total product metrics, low stock alert list, out of stock list,
    and recent inventory transactions.
    """
    total_products = Product.objects.filter(is_active=True).count()
    low_stock_qs = Product.objects.filter(is_active=True, current_stock__lte=models.F('minimum_stock'), current_stock__gt=0)
    out_of_stock_qs = Product.objects.filter(is_active=True, current_stock__lte=0)
    
    total_stock_qty = Product.objects.filter(is_active=True).aggregate(total=models.Sum('current_stock'))['total'] or 0
    recent_transactions = InventoryTransaction.objects.select_related('product', 'created_by').order_by('-created_at')[:10]

    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_qs.count(),
        'out_of_stock_count': out_of_stock_qs.count(),
        'total_stock_qty': total_stock_qty,
        'low_stock_products': low_stock_qs[:5],
        'out_of_stock_products': out_of_stock_qs[:5],
        'recent_transactions': recent_transactions,
    }
    return render(request, 'inventory/dashboard.html', context)


@admin_required
def stock_list(request):
    """
    Inventory Stock Status Table.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    status_filter = request.GET.get('status', '')

    products = Product.objects.select_related('category', 'brand').filter(is_active=True)

    if query:
        products = products.filter(
            models.Q(name__icontains=query) |
            models.Q(gujarati_name__icontains=query) |
            models.Q(sku__icontains=query) |
            models.Q(barcode__icontains=query) |
            models.Q(product_id__icontains=query)
        )

    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    if brand_id.isdigit():
        products = products.filter(brand_id=int(brand_id))

    if status_filter == 'out_of_stock':
        products = products.filter(current_stock__lte=0)
    elif status_filter == 'low_stock':
        products = products.filter(current_stock__lte=models.F('minimum_stock'), current_stock__gt=0)
    elif status_filter == 'in_stock':
        products = products.filter(current_stock__gt=models.F('minimum_stock'))

    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'categories': categories,
        'brands': brands,
        'query': query,
        'category_id': category_id,
        'brand_id': brand_id,
        'status_filter': status_filter,
    }
    return render(request, 'inventory/stock_list.html', context)


@admin_required
def history_list(request):
    """
    Full Inventory Movement Transaction History.
    """
    query = request.GET.get('q', '').strip()
    tx_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    transactions = InventoryTransaction.objects.select_related('product', 'created_by').all()

    if query:
        transactions = transactions.filter(
            models.Q(product__name__icontains=query) |
            models.Q(product__product_id__icontains=query) |
            models.Q(product__sku__icontains=query) |
            models.Q(note__icontains=query)
        )

    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)

    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    paginator = Paginator(transactions, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'transactions': page_obj.object_list,
        'query': query,
        'tx_type': tx_type,
        'date_from': date_from,
        'date_to': date_to,
        'type_choices': InventoryTransaction.TRANSACTION_TYPE_CHOICES,
    }
    return render(request, 'inventory/history.html', context)


@admin_required
def stock_adjust(request):
    """
    Admin View for Manual Stock Adjustments and Damage Recording.
    """
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            tx_type = form.cleaned_data['transaction_type']
            qty = form.cleaned_data['quantity']
            note = form.cleaned_data['note']

            try:
                tx_record = change_stock(
                    product=product,
                    quantity=qty,
                    transaction_type=tx_type,
                    user=request.user,
                    reference_type='ADJUSTMENT',
                    note=note
                )
                messages.success(
                    request,
                    f"Stock adjusted for '{product.name}'! Previous Stock: {tx_record.previous_stock} {product.unit}, New Stock: {tx_record.new_stock} {product.unit}."
                )
                return redirect('stock_list')
            except ValidationError as ve:
                messages.error(request, str(ve.message if hasattr(ve, 'message') else ve))
            except Exception as e:
                messages.error(request, f"Error updating stock: {str(e)}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        product_id = request.GET.get('product')
        initial_data = {}
        if product_id and product_id.isdigit():
            initial_data['product'] = product_id
        form = StockAdjustmentForm(initial=initial_data)

    return render(request, 'inventory/adjustment_form.html', {'form': form})
