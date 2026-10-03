from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from accounts.decorators import admin_required, cashier_or_admin_required
from categories.models import Category, Brand
from .models import Product
from .forms import ProductForm


@admin_required
def product_list(request):
    """
    Admin Product Catalog View.
    Shows full product pricing (Purchase Price, Selling Price, MRP), stock status, and filters.
    Strictly protected with @admin_required decorator.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    status_filter = request.GET.get('status', '')
    low_stock_filter = request.GET.get('low_stock', '')

    products = Product.objects.select_related('category', 'brand').all()

    # Search filter
    if query:
        products = products.filter(
            models.Q(name__icontains=query) |
            models.Q(gujarati_name__icontains=query) |
            models.Q(sku__icontains=query) |
            models.Q(barcode__icontains=query) |
            models.Q(product_id__icontains=query)
        )

    # Category filter
    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    # Brand filter
    if brand_id.isdigit():
        products = products.filter(brand_id=int(brand_id))

    # Active / Inactive filter
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)

    # Low stock filter
    if low_stock_filter == '1':
        products = products.filter(is_active=True, current_stock__lte=models.F('minimum_stock'))

    # Pagination
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
        'low_stock_filter': low_stock_filter,
    }
    return render(request, 'products/product_list.html', context)


@admin_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' ({product.product_id}) added successfully!")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the form errors below.")
    else:
        form = ProductForm()

    return render(request, 'products/product_form.html', {
        'form': form,
        'title': 'Add New Product / નવું પ્રોડક્ટ'
    })


@admin_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), pk=pk)
    recent_transactions = product.inventory_transactions.select_related('created_by').order_by('-created_at')[:10] if hasattr(product, 'inventory_transactions') else []
    return render(request, 'products/product_detail.html', {
        'product': product,
        'recent_transactions': recent_transactions
    })


@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' ({product.product_id}) updated successfully!")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the form errors below.")
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/product_form.html', {
        'form': form,
        'title': f"Edit Product: {product.name} ({product.product_id})",
        'product': product
    })


@admin_required
@require_POST
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save()
    status_str = "activated" if product.is_active else "deactivated"
    messages.success(request, f"Product '{product.name}' has been {status_str}.")
    return redirect('product_list')


@admin_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    # Check future references before hard deletion
    has_sales = hasattr(product, 'sale_items') and product.sale_items.exists()
    has_purchases = hasattr(product, 'purchase_items') and product.purchase_items.exists()
    
    if has_sales or has_purchases:
        messages.error(request, f"Cannot delete '{product.name}' because it has transaction history. Please deactivate it instead.")
    else:
        name = product.name
        pid = product.product_id
        product.delete()
        messages.success(request, f"Product '{name}' ({pid}) deleted successfully.")

    return redirect('product_list')


@cashier_or_admin_required
def barcode_list(request):
    """
    Barcode Lookup & Management view.
    Cashiers can view barcodes and selling prices. Purchase prices & cost prices are strictly excluded for Cashiers.
    """
    query = request.GET.get('q', '').strip()
    products = Product.objects.select_related('category', 'brand').all()

    if query:
        products = products.filter(
            models.Q(name__icontains=query) |
            models.Q(barcode__icontains=query) |
            models.Q(sku__icontains=query)
        )

    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/barcode_list.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'q': query
    })


@admin_required
def generate_barcode(request, pk):
    """
    Admin-only view to auto-generate a unique barcode for a product if missing.
    """
    import random
    product = get_object_or_404(Product, pk=pk)
    if not product.barcode:
        while True:
            code = f"890{random.randint(100000000, 999999999)}"
            if not Product.objects.filter(barcode=code).exists():
                product.barcode = code
                product.save(update_fields=['barcode', 'updated_at'])
                break
        messages.success(request, f"Barcode {product.barcode} generated for '{product.name}'.")
    else:
        messages.info(request, f"Product '{product.name}' already has barcode {product.barcode}.")

    return redirect('barcode_list')


@cashier_or_admin_required
def barcode_print(request, pk):
    """
    Printable Barcode Label view.
    Contains ONLY customer/pos-safe fields (Shop Name, Product Name, Barcode, Selling Price).
    Strictly excludes purchase_price, cost_price, profit, supplier data.
    """
    product = get_object_or_404(Product, pk=pk)
    quantity = int(request.GET.get('qty', 1))
    quantity = max(1, min(100, quantity))

    return render(request, 'products/barcode_print.html', {
        'product': product,
        'quantity_range': range(quantity),
    })

