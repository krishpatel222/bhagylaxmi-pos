from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from .models import Category, Brand
from .forms import CategoryForm, BrandForm


# ==========================================
# CATEGORY MANAGEMENT VIEWS (ADMIN ONLY)
# ==========================================

@admin_required
def category_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    categories = Category.objects.all()

    if query:
        categories = categories.filter(
            models.Q(name__icontains=query) | 
            models.Q(gujarati_name__icontains=query) | 
            models.Q(slug__icontains=query)
        )

    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)

    return render(request, 'categories/category_list.html', {
        'categories': categories,
        'query': query,
        'status_filter': status_filter
    })


@admin_required
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully!")
            return redirect('category_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CategoryForm()

    return render(request, 'categories/category_form.html', {
        'form': form,
        'title': 'Add New Category / નવી કેટેગરી'
    })


@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully!")
            return redirect('category_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'categories/category_form.html', {
        'form': form,
        'title': f"Edit Category: {category.name}"
    })


@admin_required
@require_POST
def category_toggle(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save()
    status_str = "activated" if category.is_active else "deactivated"
    messages.success(request, f"Category '{category.name}' has been {status_str}.")
    return redirect('category_list')


@admin_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    # Safe Deletion Check: Check if products reference this category
    if hasattr(category, 'products') and category.products.exists():
        messages.error(request, f"Cannot delete category '{category.name}' because products are linked to it. Please deactivate it instead.")
    else:
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted successfully.")
        
    return redirect('category_list')


# ==========================================
# BRAND MANAGEMENT VIEWS (ADMIN ONLY)
# ==========================================

@admin_required
def brand_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    brands = Brand.objects.all()

    if query:
        brands = brands.filter(models.Q(name__icontains=query) | models.Q(description__icontains=query))

    if status_filter == 'active':
        brands = brands.filter(is_active=True)
    elif status_filter == 'inactive':
        brands = brands.filter(is_active=False)

    return render(request, 'categories/brand_list.html', {
        'brands': brands,
        'query': query,
        'status_filter': status_filter
    })


@admin_required
def brand_add(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            brand = form.save()
            messages.success(request, f"Brand '{brand.name}' created successfully!")
            return redirect('brand_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BrandForm()

    return render(request, 'categories/brand_form.html', {
        'form': form,
        'title': 'Add New Brand / નવો બ્રાન્ડ'
    })


@admin_required
def brand_edit(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, f"Brand '{brand.name}' updated successfully!")
            return redirect('brand_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BrandForm(instance=brand)

    return render(request, 'categories/brand_form.html', {
        'form': form,
        'title': f"Edit Brand: {brand.name}"
    })


@admin_required
@require_POST
def brand_toggle(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    brand.is_active = not brand.is_active
    brand.save()
    status_str = "activated" if brand.is_active else "deactivated"
    messages.success(request, f"Brand '{brand.name}' has been {status_str}.")
    return redirect('brand_list')


@admin_required
@require_POST
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    
    if hasattr(brand, 'products') and brand.products.exists():
        messages.error(request, f"Cannot delete brand '{brand.name}' because products are linked to it. Please deactivate it instead.")
    else:
        name = brand.name
        brand.delete()
        messages.success(request, f"Brand '{name}' deleted successfully.")

    return redirect('brand_list')
